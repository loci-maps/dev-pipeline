import xml.etree.ElementTree as ET
from os.path import dirname, join

from zipfile import ZipFile

from src.data_extract import DataExtract


class EpubExtract(DataExtract):
    def __init__(self):
        super().__init__()
        self._extensions = ['epub']

    def _get_text_data(self, itemid, data, debug=False):
        try:
            root = ET.fromstring(data)
        except ET.ParseError:
            return
        body = root.find('.//{http://www.w3.org/1999/xhtml}body')
        header = body.find('.//{http://www.w3.org/1999/xhtml}h1')
        text = '\n'.join([p.text for p in body.findall('.//*') if p.text is not None]).strip()
        if header is None or header.text is None:
            # Append to previous chapter
            if len(self._data['chapters']) == 0:
                return
            self._data['chapters'][-1]['text'] += '\n' + text
            return
        if text is None:
            if debug:
                print('No text found for chapter', header.text, itemid)
            return
        title = header.text
        if text.startswith(title):
            text = text[len(title):].strip()
        if len(text) == 0:
            return
        self._data['chapters'].append({
            'id': itemid,
            'title': title,
            'text': text
        })

    def _load_data(self, filepath, debug=False):
        self._data['filepath'] = filepath
        self._data['chapters'] = []
        with ZipFile(filepath, 'r') as zip_file:
            # Read the container file to get the manifest path
            with zip_file.open('META-INF/container.xml') as container:
                root = ET.fromstring(container.read())
                manifest_path = root.find(".//*[@full-path]").get('full-path')
            if manifest_path not in zip_file.namelist():
                return 0
            # Read the manifest file to get the text files
            manifest_dir = dirname(manifest_path)
            with zip_file.open(manifest_path) as manifest:
                root = ET.fromstring(manifest.read())
                metadata = root.find('.//{http://www.idpf.org/2007/opf}metadata')
                if metadata is None:
                    return 0
                book_title = metadata.find('.//{http://purl.org/dc/elements/1.1/}title')
                if book_title is not None:
                    self._data['book_name'] = book_title.text
                creator = metadata.find('.//{http://purl.org/dc/elements/1.1/}creator')
                if creator is not None:
                    self._data['author'] = creator.text

                items = root.findall('.//{http://www.idpf.org/2007/opf}manifest/{http://www.idpf.org/2007/opf}item')
                for ref in root.find('.//{http://www.idpf.org/2007/opf}spine'):
                    item = [x for x in items if x.get('id') == ref.get('idref')][0]
                    # Only load the text files
                    if item.get('media-type') not in ('application/xhtml+xml',):
                        continue
                    if item.get('properties') in ('nav',):
                        continue
                    item_path = manifest_dir + '/' + item.get('href')
                    skip = False
                    for k in ['frontmatter', 'backmatter', 'cover', 'copyright', 'signup']:
                        if k in item_path:
                            skip = True
                            break
                    if skip:
                        continue
                    try:
                        with zip_file.open(item_path) as text_file:
                            self._get_text_data(item.get('id'), text_file.read(), debug)
                    except KeyError:
                        if debug:
                            print('Could not find', item_path)
                        continue
        return len(self._data['chapters'])

    def get_book_name(self, _):
        """
        Get the book name
        :param _: Does Nothing
        :return: The book name
        """
        return self._data['book_name']

    def get_author(self, _):
        """
        Get the book author
        :param _: Does Nothing
        :return: The book author
        """
        return self._data['author']

    def get_chapter_name(self, ix):
        """
        Get the name of the Xth chapter
        :param ix: The index of chapter
        :return: The chapter name
        """
        return self._data['chapters'][ix]['title']

    def get_combined_title(self, ix):
        """
        Get the name of the Xth chapter
        :param ix: The index of chapter
        :return: The chapter name
        """
        return self._data['book_name'] + ' - ' + self._data['chapters'][ix]['title']

    def get_chapter_text(self, ix):
        """
        Get the text of the Xth chapter
        :param ix: The index of chapter
        :return: The chapter text
        """
        return self._data['chapters'][ix]['text']


EPUB_EMBEDDINGS = {
    'filename': EpubExtract.get_combined_title,
    'text': EpubExtract.get_chapter_text
}


