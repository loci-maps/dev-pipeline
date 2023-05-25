from os.path import join
from pickle import dump, load

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from scipy.cluster.hierarchy import dendrogram
from umap import UMAP
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE


REDUCTION_METHODS = {
    'pca': PCA,
    'umap': UMAP,
    'tsne': TSNE
}


def save_pickle(obj, file_path=join('output', 'tree.pkl')):
    with open(file_path, 'wb') as f:
        dump(obj, f)


def load_pickle(file_path=join('output', 'tree.pkl')):
    with open(file_path, 'rb') as f:
        return load(f)


def save_npz(obj, file_path=join('output', 'embeddings.npz')):
    np.savez(file_path, embeddings=obj[0], filenames=obj[1])


def load_npz(file_path=join('output', 'embeddings.npz')):
    data = np.load(file_path, allow_pickle=True)
    return data['embeddings'], data['filenames']
    # return pd.DataFrame(data['embeddings'], index=data['filenames'])


def read_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()


def normalize(embeddings):
    return (embeddings - embeddings.min()) / (embeddings.max() - embeddings.min())


def reduce_embeddings(embeddings, method):
    for name, reducer in REDUCTION_METHODS.items():
        if method.startswith(name):
            components = int(method[len(name):])
            instance = reducer(n_components=components)
            return normalize(instance.fit_transform(embeddings))
    raise ValueError(f"Unknown reduction {method}")


def plot_embeddings(embeddings, filenames, colors, plot_title='Reduction Plot'):
    if colors is None:
        plt.scatter(embeddings[:, 0], embeddings[:, 1])
    else:
        plt.scatter(embeddings[:, 0], embeddings[:, 1], c=colors)

    if filenames is not None:
        for i, txt in enumerate(filenames):
            if colors is None:
                plt.annotate(txt, (embeddings[i, 0], embeddings[i, 1]), fontsize=8)
            else:
                plt.annotate(txt, (embeddings[i, 0], embeddings[i, 1]), fontsize=8, color=colors[i])

    plt.title(plot_title)
    plt.show()


def plot_dendrogram(linked, filenames, colors):
    plt.figure(figsize=(15, 7))
    dendrogram(linked, leaf_rotation=45, labels=filenames, link_color_func=lambda link_id: colors[link_id])
    plt.title('Hierarchical Clustering Dendrogram with Filenames and PCA5 Link Colors')
    plt.show()


# Define a function to recursively traverse the tree and store information in the leaves
def store_info_in_leaves(node, filenames, embeddings, umap2, pca5, tsne2):
    if node.is_leaf():
        node.data = {
            'filename':  filenames[node.id],
            'embedding': embeddings[node.id],
            'umap2':     umap2[node.id],
            'pca5':      pca5[node.id],
            'tsne2':     tsne2[node.id]
        }
    else:
        store_info_in_leaves(node.left, filenames, embeddings, umap2, pca5, tsne2)
        store_info_in_leaves(node.right, filenames, embeddings, umap2, pca5, tsne2)


def chunk_text(text, chunk_size=512):
    """
    Splits text into tokens
    :param text: The raw text
    :param chunk_size: The maximum number of tokens
    :return: The list of chunks
    """
    tokens = text.split()
    chunks = []
    chunk = []

    for token in tokens:
        if len(chunk) + len(token) + 1 <= chunk_size:
            chunk.append(token)
        else:
            chunks.append(' '.join(chunk))
            chunk = [token]

    if len(chunk) > 0:
        chunks.append(' '.join(chunk))

    return chunks

