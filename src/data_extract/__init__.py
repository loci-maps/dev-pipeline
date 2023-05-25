from __future__ import annotations

import re
from os import listdir
from os.path import basename, isdir, join

import pandas as pd
from tqdm import tqdm

from src.utils import read_file


class DataExtract:
    def __init__(self):
        self._data = {}
        self._extensions = ['txt']

    def set_valid_extensions(self, exts):
        self._extensions = exts

    @staticmethod
    def _glob_path(path):
        """
        Recursively searches through the path and returns a list of all files
        :param path: The directory to search in
        :return: A list of paths
        """
        if not isdir(path):
            raise ValueError(f"{path} is not a directory")
        out = []
        for file in listdir(path):
            filepath = join(path, file)
            out.append(filepath)
            if isdir(filepath):
                out += DataExtract._glob_path(filepath)
        return out

    def _valid(self, filename):
        """
        Checks if the file is valid
        :return: True if valid, False otherwise
        """
        ext = filename.rsplit('.', 1)[-1]
        return ext in self._extensions

    def _glob_valid(self, path):
        """
        Combs through all files and directories in the path and returns paths to files this extractor can process
        :param path: The path to search in
        :return: A list of paths
        """
        paths = []
        for filepath in self._glob_path(path):
            if not self._valid(filepath):
                continue
            paths.append(filepath)
        return paths

    def _load_data(self, filepath):
        """
        Load the data from the file
        :param filepath: The path to the file
        :return: The count of objects in this file
        """
        self._data['filepath'] = filepath
        self._data['raw_data'] = read_file(filepath)
        return 1

    def get_file(self, _):
        """
        Read the raw text from the file
        :param _: Does Nothing
        :return: A copy of the raw text
        """
        return self._data['raw_data']

    def get_filename(self, _):
        """
        Get the filename from the filepath
        :param _: Does Nothing
        :return: A copy of the filename
        """
        return basename(self._data['filepath']).rsplit('.', 1)[0]

    def get_links(self, _):
        """
        Get the links from the raw text
        :param _: Does Nothing
        :return: A list of links
        """
        if 'links' not in self._data:
            links = re.findall(r"\[\[.*?]]", self._data['raw_data'])
            self._data['links'] = [link.strip("[[").strip("]]") for link in links]
        return self._data['links']

    def extract_data(self, input_path, embedding_struct, debug=False):
        """
        Extracts data from the input path utilizing the passed struct
        See DEFAULT_EMBEDDING for an example
        :param input_path: The path to the input directory
        :param embedding_struct: The struct to use to extract data
        :return: A dataframe containing the extracted data
        """
        if not isdir(input_path):
            raise ValueError(f"{input_path} is not a directory")
        files_to_extract = self._glob_valid(input_path)
        if len(files_to_extract) == 0:
            raise ValueError(f"No valid files found in {input_path}")
        if debug:
            print(f'Extracting data from {len(files_to_extract)} files')
        data = []
        success_count = 0
        for filepath in tqdm(files_to_extract, desc='Extracting data'):
            count = self._load_data(filepath)
            if count == 0:
                if debug:
                    print('Error loading data from', filepath)
                continue
            success_count += 1
            for ix in range(count):
                file_data = {}
                for key, method in embedding_struct.items():
                    file_data[key] = method(self, ix)
                data.append(file_data)
        if debug:
            print(f'Successfully extracted data from {success_count} files')
        return pd.DataFrame(data, columns=embedding_struct.keys())


DEFAULT_EMBEDDING = {
    'filename': DataExtract.get_filename,
    'text': DataExtract.get_file
}
