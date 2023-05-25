from os import makedirs
from typing import Optional
from uuid import uuid4

import pandas as pd

from hashlib import sha1
from os.path import basename, exists, join

from src.data_extract.utils import get_extractor_struct_for_extension, get_extractor_for_extension, glob_files

import threading


class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


def hash_string(string):
    return sha1(string.encode('utf-8')).hexdigest()


class Embeddings(StoppableThread):
    def __init__(self, info, **kwargs):
        self._info = info
        super().__init__(**kwargs)

    def run(self) -> Optional[str]:
        self._info['name'] = uuid4().hex
        print('Running Embeddings', self._info['name'])
        print(self._info)
        if self.stopped():
            return None
        # Stage 1: Glob Files
        # data = self.load_data()
        if self.stopped():
            return None
        # Stage 3: Run Embedding
        embedding = self.create_embedding(data)
        if self.stopped():
            return None
        # Stage 4: Save Embedding

        return self._info['name']

    def load_data(self):
        data = {}
        for input_folder in self._info['input_folders']:
            extensions = input_folder['extensions']
            valid_files = glob_files(input_folder['path'], extensions)
            extractors = {extension: get_extractor_for_extension(extension)() for extension in extensions}
            for file in valid_files:
                file_hash = hash_string(file)
                extractor = extractors[file.rsplit('.', 1)[1]]
                data[file_hash] = extractor.extract_data(file)
                if self.stopped():
                    return {}
        return data

    def create_embedding(self, data):
        embedding = None
        for file_hash, file_data in data.items():

        # for data_name, dataframe in data.items():
        #     embedding = dataframe
        #     if self.stopped():
        #         return None
        return embedding
