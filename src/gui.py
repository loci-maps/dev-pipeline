import platform

from src.gui_utils import Embeddings

if platform.system() == 'Windows':
    from win32api import GetSystemMetrics
    width, height = GetSystemMetrics(0), GetSystemMetrics(1)
elif platform.system() == 'MacOS':
    from AppKit import NSScreen
    frame = NSScreen.mainScreen().frame()
    width, height = frame.size.width, frame.size.height
else:
    width, height = 1920, 1080
    print('WARNING: Unknown OS, defaulting to 1920x1080')

window_width = width * 2 // 3
window_height = height * 2 // 3
left = (width - window_width) // 2
top = (height - window_height) // 2

from kivy.config import Config
Config.set('graphics', 'width', window_width)
Config.set('graphics', 'height', window_height)
Config.set('graphics', 'left', left)
Config.set('graphics', 'top', top)

from os import listdir, makedirs
from os.path import exists, expanduser, isdir, join

from kivy.app import App
from kivy.clock import Clock
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.recycleview import RecycleView
from kivy.uix.label import Label
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.tabbedpanel import TabbedPanel
from kivy_garden.filebrowser import FileBrowser

from configparser import ConfigParser
import multiprocessing
from uuid import uuid5

parser = ConfigParser()

DATA_TYPES = [
    ('Text File', 'txt'),
    ('Markdown File', 'md'),
    ('EPUB File', 'epub'),
]

if not exists('config.ini'):
    print('No config file found. Creating blank config file.')
    parser.set('cohere', 'api_key', '')
    for _, ext in DATA_TYPES:
        parser.set('data_types', ext, 'True')
    parser.set('data', 'data_folder', 'data')
    print('Pleas edit config.ini and run again.')
    exit(1)
else:
    parser.read('config.ini')

# Make the data folder if it does not exist
if not exists(parser.get('data', 'data_folder')):
    print('Data folder not found. Creating data folder.')
    makedirs(parser.get('data', 'data_folder'))


def _get_valid(path, valid):
    items = [join(path, x) for x in listdir(path)]
    count = 0
    file_types = set()
    for item in items:
        if isdir(item):
            c, f = _get_valid(item, valid)
            count += c
            file_types = file_types.union(f)
        else:
            ext = item.rsplit('.', 1)[-1]
            if ext in valid:
                count += 1
                file_types.add(ext)
    return count, file_types


def get_valid_files(folder, valid=None):
    if valid is None:
        valid = [y for x, y in DATA_TYPES]
    return _get_valid(folder, valid)


class InsetCheckBox(RelativeLayout):
    checked = BooleanProperty(False)

    def __init__(self, **kwargs):
        self._check = None
        super().__init__(**kwargs)
        self._check = self.ids.check_box
        self._check.active = self.checked
        self._check.bind(active=self.on_active)

    def on_checked(self, _, value):
        if self._check is None:
            return
        self._check.active = value

    def on_active(self, _, value):
        if value != self.checked:
            self.checked = value
            self.parent.c_enabled(self, value)


class CenteredLabel(Label):
    pass


class SelectableLabel(RelativeLayout):
    root = ObjectProperty(None)
    title = StringProperty('Title')
    info = ListProperty(['Info'])
    enabled = BooleanProperty(False)
    index = NumericProperty(1)
    type = StringProperty('')
    sizes = ListProperty([])

    def remove(self):
        self.root.remove(self)

    def c_enabled(self, _, v):
        if self.root is None:
            return
        for c in self.root.data:
            if c['index'] == self.index:
                c['enabled'] = v
                break

    def __init__(self, **kwargs):
        self.font_size = 20
        super().__init__(**kwargs)
        self.bindings = {}

    def recalculate(self):
        if len(self.sizes) != len(self.children):
            return
        offset = 0
        for ix, child in enumerate(reversed(self.children)):
            size = self.sizes[ix]
            child.size_hint = (size, 1)
            child.pos_hint = {'x': offset}
            offset += size

    def on_type(self, *_):
        if self.type == 'data_type':
            self.add(CenteredLabel(font_size=self.font_size), 'title', 'text')
            self.add(CenteredLabel(font_size=self.font_size), 'info', 'text', 0)
            self.add(InsetCheckBox(checked=self.enabled), 'enabled', 'checked')
        elif self.type == 'input_folder':
            self.add(CenteredLabel(font_size=self.font_size), 'title', 'text')
            self.add(CenteredLabel(font_size=self.font_size), 'info', 'text', 0)
            self.add(CenteredLabel(font_size=self.font_size), 'info', 'text', 1)
            self.add(InsetCheckBox(checked=self.enabled), 'enabled', 'checked')
            self.add_widget(Button(font_size=self.font_size, text='Remove', on_release=lambda _: self.remove()))
        self.recalculate()

    def _update_property(self, widget, attribute, value, index):
        if index != -1:
            value = value[index]
        setattr(widget, attribute, value)

    def add(self, widget, property, attribute, index=-1):
        self.bind(**{property: lambda _, value: self._update_property(widget, attribute, value, index)})
        self._update_property(widget, attribute, getattr(self, property), index)
        self.add_widget(widget)


class HeaderRecycleView(RecycleView):
    headers = ObjectProperty(None)

    def __init__(self, **kwargs):
        self._headers = []
        super().__init__(**kwargs)

    def on_headers(self, _, value):
        if value is None:
            return
        offset = 0
        for header, size in self._headers:
            header_label = CenteredLabel(font_size=20, text=header, size_hint=(size, 1), pos_hint={'x': offset}, valign='middle', halign='center')
            value.add_widget(header_label)
            offset += size


class EmbeddingsRecycleView(HeaderRecycleView):
    def __init__(self, **kwargs):
        # Name, Data Types, Type, File Count, Chunk Count, PCA, TSNE, UMAP, Selected
        super().__init__(**kwargs)
        self._headers = [
            ('Name', 0.3),
            ('Data Types', 0.2),
            ('Type', 0.1),
            ('File Count', 0.1),
            ('Chunk Count', 0.1),
            ('PCA', 0.05),
            ('TSNE', 0.05),
            ('UMAP', 0.05),
            ('Selected', 0.05),
        ]
        self.data = []
        # for ix, (key, data) in enumerate(parser.items('embeddings')):
        #     self.data.append({
        #         'root': self,
        #         'sizes': [y for x, y in self._headers],
        #         'info': [],
        #         'title': key,
        #         'index': ix,
        #         'enabled': data[-1] == 'True',
        #     })


class DataTypesRecycleView(HeaderRecycleView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._headers = [('Title', 0.45), ('Extension', 0.45), ('Enabled', 0.1)]
        self.data = []
        for ix, (key, enabled) in enumerate(parser.items('data_types')):
            title = DATA_TYPES[ix][1]
            self.data.append({
                'root':    self,
                'sizes':   [y for x, y in self._headers],
                'info':    [key],
                'title':   title,
                'enabled': enabled == 'True',
                'index':   ix,
                'type':    'data_type',
            })

    def disable_all(self):
        for item in self.data:
            item['enabled'] = False
        self.refresh_from_data()

    def enable_all(self):
        for item in self.data:
            item['enabled'] = True
        self.refresh_from_data()


class InputFoldersRecycleView(HeaderRecycleView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = []
        self._popup = None
        self._last_path = None
        self._headers = [('Path', 0.55), ('Detected Files', 0.1), ('Supported File Types', 0.15), ('Enabled', 0.1), ('Remove', 0.1)]
        for ix, (path, data) in enumerate(parser.items('input_folders')):
            enabled, item_count, valid_types = data.split('|')
            self.data.append({
                'root':    self,
                'sizes':   [y for x, y in self._headers],
                'info':    [item_count, valid_types],
                'title':   path.replace('&col', ':'),
                'enabled': enabled == 'True',
                'index':   len(self.data),
                'type':    'input_folder',
            })

    def _add_folder(self, path):
        if path == '':
            return
        item_count, file_types = get_valid_files(path)
        file_type_string = ', '.join(list(file_types)[:5])
        if len(file_types) > 5:
            file_type_string += ', and {} others'.format(len(file_types) - 5)
        self.data.append({
            'root':    self,
            'sizes':   [y for x, y in self._headers],
            'info':    [str(item_count), file_type_string],
            'title':   path.lower(),
            'enabled': True,
            'index':   len(self.data),
            'type':    'input_folder',
        })

        self.refresh_from_data()

    def add_folder(self, text_input, error_label):
        if text_input.text == '':
            error_label.text = 'Folder name cannot be empty'
            Clock.schedule_once(lambda dt: setattr(error_label, 'text', ''), 2)
            return
        if not exists(text_input.text):
            error_label.text = 'Folder does not exist'
            Clock.schedule_once(lambda dt: setattr(error_label, 'text', ''), 2)
            return
        self._add_folder(text_input.text)
        text_input.text = ''

    def browse_folder(self):
        path = ''
        if self._last_path is not None:
            path = self._last_path
        if not exists(path):
            path = expanduser('~')
        browser = FileBrowser(select_string='Select', dirselect=True, path=path)
        browser.bind(on_success=self.do_add_folder, on_canceled=self.cancel_browse)
        self._popup = Popup(title="Load file", content=browser, size_hint=(0.9, 0.9))
        self._popup.open()

    def cancel_browse(self, instance):
        if len(instance.selection) > 0:
            self._last_path = instance.selection[0]
        self._popup.dismiss()
        self._popup = None

    def do_add_folder(self, instance):
        if len(instance.selection) == 0:
            if len(instance.path) == 0:
                return
            path = instance.path
        else:
            path = instance.selection[0]
        self._popup.dismiss()
        self._popup = None
        self._last_path = path
        self._add_folder(path)

    def remove_all(self):
        self.data = []
        self.refresh_from_data()

    def remove(self, widget):
        to_remove = None
        for item in self.data:
            if item['index'] == widget.index:
                to_remove = item
                break
        self.data.remove(to_remove)
        self.refresh_from_data()

    def disable_all(self):
        for item in self.data:
            item['enabled'] = False
        self.refresh_from_data()

    def enable_all(self):
        for item in self.data:
            item['enabled'] = True
        self.refresh_from_data()


class CreateEmbeddings(RelativeLayout):
    def __init__(self, pipeline, options, **kwargs):
        self.pipeline = pipeline
        self.options = options
        self._status = 'not_started'
        self._embedding_type = None
        self._embedding_thread = None
        super().__init__(**kwargs)

        default_type = options['type']

        for name, option in options['embedding_types'].items():
            button = ToggleButton(group='embedding_type', text=name, allow_no_selection=False)
            button.state = 'down' if name == default_type else 'normal'
            button.bind(on_release=self.change_embedding_type)
            self.ids.embedding_type.add_widget(button)
        self.change_embedding_type(default_type)
        self.ids.chunk_size.value = options['chunk_size']

    def set_status(self, status):
        self.ids.embedding_status.text = status

    def embedding(self):
        info = {
            'input_folders': [],
            'output_folder': parser.get('data', 'data_folder'),
            'force': self.ids.force_reload.state == 'down',
        }

        for item in self.pipeline.ids.input_folders_rv.data:
            if item['enabled']:
                info['input_folders'].append({
                    'path': item['title'],
                    'extensions': item['info'][1].split(', '),
                })

        if self._embedding_type == 'Cohere':
            info['chunk_size'] = self.ids.chunk_size.value
        else:
            raise NotImplementedError('Only Cohere Supported')

        if self._status == 'not_started':
            self._status = 'running'
            self.ids.interaction.text = 'Stop'
            self.ids.embedding_status.text = 'Running'
            self._embedding_thread = Embeddings(info)
            self._embedding_thread.start()
            Clock.schedule_interval(self.check_finish, 0.25)
        elif self._status == 'running':
            # TODO: Stop the embedding
            if self._embedding_thread.is_alive():
                self._embedding_thread.stop()
            self._status = 'not_started'
            self.ids.embedding_status.text = 'Stopping'
            self.ids.interaction.text = 'Start'
            self.ids.interaction.disabled = True

    def check_finish(self, _):
        if not self._embedding_thread.is_alive():
            if self._status == 'running':
                self.ids.embedding_status.text = 'Finished'
                self.ids.interaction.text = 'Start'
            elif self._status == 'not_running':
                self.ids.embedding_status.text = 'Terminated'
                self.ids.interaction.disabled = False

    def change_embedding_type(self, new_type):
        self._embedding_type = new_type
        self.ids.chunk_size.min = 1
        maximum = self.options['embedding_types'][new_type]['max_chunk_size']
        self.ids.chunk_size.max = maximum
        self.ids.chunk_size.value = self.ids.chunk_size.max - 1
        self.ids.chunk_size.step = 1
        self.ids.max_chunk_size.text = str(maximum)
        self.ids.current_chunk_size.text = str(maximum)


class Pipeline(TabbedPanel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._popup = None

    def create_embeddings(self):
        # TODO: Get the data types we want to use
        data_types = [x['info'][0] for x in self.ids.data_types_rv.data if x['enabled']]
        input_folders = [x['title'] for x in self.ids.input_folders_rv.data if x['enabled']]
        # TODO: Get the input folders we want to use

        self.options = {
            'type': 'Cohere',
            'chunk_size': 512,
            'embedding_types': {
                'Cohere': {
                    'max_chunk_size': 512,

                }
            }
        }

        self._popup = Popup(content=CreateEmbeddings(self, self.options), size_hint=(0.9, 0.9), title='Create Embeddings')
        self._popup.open()
        # Embedding Type: Cohere | ??
        # Chunk Size: 0 -> Max


class LociLabs(App):
    def on_stop(self):
        print('Stopping...')
        data_types = [(x['info'][0], x['enabled']) for x in self.root.ids.data_types_rv.data]
        for ext, enabled in data_types:
            print(ext, enabled)
            parser.set('data_types', ext, str(enabled))
        input_folders = [(x['title'], x['enabled'], x['info'][0], x['info'][1]) for x in self.root.ids.input_folders_rv.data]
        if not parser.has_section('input_folders'):
            parser.add_section('input_folders')
        for folder, enabled, item_count, valid_types in input_folders:
            parser.set('input_folders', folder.replace(':', '&col'), f'{enabled}|{item_count}|{valid_types}')
        with open('config.ini', 'w') as configfile:
            parser.write(configfile)


if __name__ == '__main__':
    app = LociLabs()
    app.run()
