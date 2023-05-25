from os import getcwd
from subprocess import run
from configparser import ConfigParser, NoOptionError

import numpy as np
import pandas as pd
from os.path import basename, exists, join

from scipy.cluster.hierarchy import dendrogram, linkage, to_tree

from src.color_utils import blend_colors, blend_pca_colors, color_to_hex
from src.utils import load_npz, load_pickle, plot_dendrogram, plot_embeddings, read_file, reduce_embeddings, save_npz, save_pickle, store_info_in_leaves
from src.data_extract.utils import get_extractor_struct_for_extension, get_extractor_for_extension
import src.data_extract.cohere_api as capi

if not getcwd().endswith('fractal-embeddings'):
    print('Please run this script from the root directory of the project.')
    exit(1)


def load_data(config):
    try:
        input_folders = config.get('data', 'input_folders')
        output_folder = config.get('data', 'output_folder')
    except NoOptionError:
        print('Specify input_folders and output_folder in config.ini under [data] header')
        exit(1)

    data = {}
    for input_regex in input_folders.split(','):
        extension, input_folder = input_regex.split(':', 1)
        data_name = basename(input_folder)
        data_path = join(output_folder, f'{data_name}.pkl')
        if exists(data_path):
            print(f'Data already extracted. Skipping.')
            data[data_name] = pd.read_pickle(data_path)
        else:
            extractor = get_extractor_for_extension(extension)()
            extractor.set_valid_extensions([extension])
            struct = get_extractor_struct_for_extension(extension)
            data[data_name] = extractor.extract_data(input_folder, struct)
            data[data_name].to_pickle(data_path)
    return data


def get_embeddings(config):
    api_key = None
    try:
        output_folder = config.get('data', 'output_folder')
    except NoOptionError:
        print('Specify output_folder in config.ini under [data] header')
        exit(1)

    data = load_data(config)

    embeddings = {}
    for data_name, dataframe in data.items():
        embedding_path = join(output_folder, f'{data_name}_embeddings.npz')
        if exists(embedding_path):
            print('Embeddings already extracted. Skipping.')
            embeddings[data_name] = load_npz(embedding_path)
        else:
            if api_key is None:
                try:
                    api_key = config.get('cohere', 'api_key')
                except NoOptionError:
                    print('Please paste your API key in config.ini under a [cohere] header.')
                    exit(1)
            embeddings[data_name] = capi.create_embeddings(dataframe, api_key)
            save_npz(embeddings[data_name], embedding_path)
    return embeddings


def get_combined_embeddings(config):
    try:
        output_folder = config.get('data', 'output_folder')
    except NoOptionError:
        print('Specify output_folder in config.ini under [data] header')
        exit(1)

    if exists(join(output_folder, 'combined_embeddings.npz')):
        print('Combined embeddings already extracted. Skipping.')
        return load_npz(join(output_folder, 'combined_embeddings.npz'))
    embeddings = get_embeddings(config)
    combined_embeddings = np.concatenate([embedding[0] for embedding in embeddings.values()], axis=0)
    combined_filenames = np.concatenate([embedding[1] for embedding in embeddings.values()], axis=0)
    save_npz((combined_embeddings, combined_filenames), join(output_folder, 'combined_embeddings.npz'))
    return combined_embeddings, combined_filenames


def get_reduced_embeddings(config):
    try:
        reduction_methods = config.get('data', 'reduction_methods')
        output_folder = config.get('data', 'output_folder')
    except NoOptionError:
        reduction_methods = ['pca5', 'umap2', 'tsne2']

    combined_embeddings, combined_filenames = get_combined_embeddings(config)

    reduced_embeddings = {}
    for method in reduction_methods:
        reduction_path = join(output_folder, f'{method}_embeddings.npz')
        if exists(reduction_path):
            print(f'{method} embeddings already extracted. Skipping.')
            reduced_embeddings[method] = load_npz(reduction_path)
        else:
            reduced_embeddings[method] = reduce_embeddings(combined_embeddings, method), combined_filenames
            save_npz(reduced_embeddings[method], reduction_path)

    colors = None
    if 'pca5' in reduction_methods:
        colors = reduced_embeddings['pca5'][0][:, 2:5]
    for method in reduction_methods:
        plot_title = f'{method.upper()[:-1]} {method[-1]} Components'
        plot_embeddings(*reduced_embeddings[method], colors, plot_title)
        plot_embeddings(reduced_embeddings[method][0], None, colors, plot_title)

    return reduced_embeddings


def main():
    # 1. Load Configuration Data
    if not exists('config.ini'):
        print('Please make a text file named "config.ini" in the root directory of this project and paste your API key in it under a [cohere] header.')
        exit(1)

    config = ConfigParser()
    config.read('config.ini')

    get_reduced_embeddings(config)

    # 7. Cluster the embeddings
    # linked = linkage(combined_embeddings, method='ward')
    # 8. Plot Dendrogram
    # cluster_colors = blend_pca_colors(linked, colors, len(combined_filenames))
    # plot_dendrogram(linked, combined_filenames, color_to_hex(cluster_colors))



if __name__ == "__main__":
    main()
