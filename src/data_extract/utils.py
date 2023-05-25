from os import listdir
from os.path import isdir, join

from src.data_extract import DataExtract
from src.data_extract.epub import EPUB_EMBEDDINGS, EpubExtract


def get_extractor_for_extension(ext):
    if ext in ('md', 'txt'):
        return DataExtract
    elif ext in ('epub',):
        return EpubExtract
    else:
        raise ValueError(f"Unknown extractor for extension {ext}")


def get_extractor_struct_for_extension(ext):
    if ext in ('md', 'txt'):
        return {
            'filename': DataExtract.get_filename,
            'text': DataExtract.get_file,
            'links': DataExtract.get_links
        }
    elif ext in ('epub',):
        return EPUB_EMBEDDINGS
    else:
        raise ValueError(f"Unknown extractor for extension {ext}")


def glob_files(path, supported):
    files = []
    for file in listdir(path):
        name, ext = file.rsplit('.', 1)
        if ext not in supported:
            continue
        if isdir(join(path, file)):
            files += glob_files(join(path, file), supported)
        else:
            files.append(join(path, file))
    return files

