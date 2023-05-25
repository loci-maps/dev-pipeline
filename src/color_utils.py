import matplotlib.colors as mcolors
import numpy as np


# Adds colors for linkages by blending the leave colors together, recursively
# if t is 1, color2 is returned, if it is 0, color1 is
def blend_colors(color1, color2, t):
    r1, g1, b1 = color1
    r2, g2, b2 = color2

    r = r1 * (1 - t) + r2 * t
    g = g1 * (1 - t) + g2 * t
    b = b1 * (1 - t) + b2 * t

    return r, g, b


def blend_pca_colors(linked, colors, file_count):
    for row in linked:
        cluster1_id = int(row[0])
        cluster2_id = int(row[1])

        if cluster1_id < file_count:  # it is a sample/leaf
            cluster1_size = 1
        else:
            cluster1_size = linked[file_count - cluster1_id][-1]

        if cluster2_id < file_count:  # it is a sample/leaf
            cluster2_size = 1
        else:
            cluster2_size = linked[file_count - cluster2_id][-1]

        # If a cluster is huge and is blended with a leaf, the color should be mostly the leaf color
        # Can try different weighting here
        t = cluster2_size / (cluster1_size + cluster2_size)

        color1 = colors[cluster1_id]
        color2 = colors[cluster2_id]

        colors = np.vstack((colors, blend_colors(color1, color2, t)))
    return colors


def color_to_hex(colors):
    return [mcolors.to_hex(color) for color in colors]
