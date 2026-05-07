import os
from typing import List, Tuple, Union

import numpy as np

from vpt_segmentation_packing.util.general_data import form_transformation_matrix
from vpt_segmentation_packing.util.io import load_binary_analysis_result
from vpt_segmentation_packing.util.unpacking import unpack_lods


def load_polygons(
    lod: int, manifest: dict, manifestCells: dict, tileBytes: bytes, tileNumber: int
) -> Tuple[List, np.ndarray]:
    expWidth = manifest["mosaic_width_pixels"]
    expHeight = manifest["mosaic_height_pixels"]
    tilesGrid = manifestCells["tiles"]
    transformMatrix = form_transformation_matrix(manifest["bbox_microns"], expWidth, expHeight)

    lodTilesGrid = tilesGrid[lod]
    i = tileNumber % lodTilesGrid[0]
    j = tileNumber // lodTilesGrid[0]

    cornerPoint = (np.uint32(expWidth / lodTilesGrid[0] * i), np.uint32(expHeight / lodTilesGrid[1] * j))

    polyList, cellMap = unpack_lods(tileBytes, lod, (expWidth, expHeight), tilesGrid, transformMatrix, cornerPoint)

    return polyList, cellMap


def load_lod(lod: int, zPlane: int, manifest: dict, manifestCells: dict, outputDir: Union[str, os.PathLike]):
    tilesGrid = manifestCells["tiles"]
    tiles_x_num, tiles_y_num = tilesGrid[lod]
    polygonsList = []
    for j in range(tiles_y_num):
        for i in range(tiles_x_num):
            tileNumber = tiles_x_num * j + i
            tileBytes = load_binary_analysis_result(f"tile{tileNumber}", f"{outputDir}/z-plane{zPlane}/Lod{lod}")
            polyList, _ = load_polygons(lod, manifest, manifestCells, tileBytes, tileNumber)
            polygonsList.extend(polyList)

    return polygonsList
