from typing import Iterable

import geopandas as gpd
from vpt_core import log
from vpt_core.io.regex_tools import ImagePath

char_encoding = {
    "<": "_LT_",
    ">": "_GT_",
    ":": "_COL_",
    '"': "_QUO_",
    "/": "_FSL_",
    "\\": "_BSL_",
    "|": "_PIP_",
    "?": "_QST_",
    "*": "_AST_",
    "%": "_PRC_",
}

char_decoding = {v: k for k, v in char_encoding.items()}


def validate_z_layers_number(img_paths: Iterable[ImagePath], boundaries: gpd.GeoDataFrame):
    bnd_z_layers = set(boundaries["ZIndex"].unique())
    img_z_layers = set(img_path.z_layer for img_path in img_paths)

    for z_layer in bnd_z_layers:
        if z_layer not in img_z_layers:
            log.warning(f"There are no images for z-layer {z_layer}")
