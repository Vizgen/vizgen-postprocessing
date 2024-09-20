from collections import namedtuple

from vpt.utils.general_data import load_texture_coords, load_texture_matrix

ImageParams = namedtuple("ImageParams", ["micronToPixelMatrix", "textureSize"])


def load_image_parameters(datasetPath: str) -> ImageParams:
    return ImageParams(load_texture_matrix(datasetPath), load_texture_coords(datasetPath))
