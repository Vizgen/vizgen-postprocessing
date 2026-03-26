"""Module for general functions, using in different parts of project"""
import json
import math
from collections import namedtuple

import numpy as np

PACK_FACTOR = 2**24

MAX_WEB_TILE_SIZE = (250, 400, 1000)

EXPORT_FOLDER = "VizExport"
WEB_EXPORT_FOLDER = "VizWebExport"

ImageInfo = namedtuple("ImageInfo", "textureWidth textureHeight transformationMatrix")


def grid_size_calculate(textureSize, transformationMatrix, maxSize: int) -> tuple[int, int]:
    """Calculate voxel grid count based on experiment size.
    maxSize in microns - is maximum that voxel side could be for proper
    visualization.
    """
    expWidth = textureSize[0] / transformationMatrix[0][0]
    expHeight = textureSize[1] / transformationMatrix[1][1]

    return math.ceil(expWidth / maxSize), math.ceil(expHeight / maxSize)


def get_mosaic(folder):
    """Open picture manifest, deserialize from json file to dictionary.

    Args:
        folder: (str): Path to task, that builds mosaic.
    Returns:
         Dict from json file.
    """
    fileNameJson = f"{folder}/manifest.json"
    with open(fileNameJson) as jsonFile:
        data = json.load(jsonFile)
    return data


def form_transformation_matrix(micronExtents, textureWidth, textureHeight) -> np.ndarray:
    """Get transformation matrix.

    Transformation matrix is used for pixels to microns transformation.
    Usage: create vector3 with pixel coordinate, then multiply by this
    matrix, and as result you will receive point coordinate in microns.

    Args:
        micronExtents: Array with 4 elements xMin, yMin, xMax, yMax for
            all field extents in microns.
        textureWidth: Width of picture range of values.
        textureHeight: Height of picture range of values.
    Returns:
        3*3 ndarray matrix for transformation.
    """
    xExtMin = micronExtents[0]
    yExtMin = micronExtents[1]
    xExtMax = micronExtents[2]
    yExtMax = micronExtents[3]
    ax = textureWidth / (xExtMax - xExtMin)
    bx = -textureWidth * xExtMin / (xExtMax - xExtMin)
    ay = textureHeight / (yExtMax - yExtMin)
    by = -textureHeight * yExtMin / (yExtMax - yExtMin)

    return np.asarray([[ax, 0, bx], [0, ay, by], [0, 0, 1]], dtype=np.float32)


def extend_btr_by_fixed_str(btr: bytearray, string: str, maxBytesCount: int):
    """Extends bytearray by bytes from string with size chunk equal to
    maxBytesCount.

    Args:
        btr: Extending bytearray.
        string: Original string.
        maxBytesCount: Chunk size.
    """

    nameLen = len(string)
    if nameLen > maxBytesCount:
        string = string[0:maxBytesCount]
        nameLen = maxBytesCount

    btr.extend(map(ord, string))
    delta = maxBytesCount - nameLen
    for _ in range(delta):
        btr.append(0)
