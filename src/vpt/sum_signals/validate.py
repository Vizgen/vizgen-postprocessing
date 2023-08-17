from typing import Iterable

import geopandas as gpd
from vpt_core.io.regex_tools import ImagePath


def validate_z_layers_number(img_paths: Iterable[ImagePath], boundaries: gpd.GeoDataFrame):
    bnd_z_layers = set(boundaries["ZIndex"].unique())
    img_z_layers = set(img_path.z_layer for img_path in img_paths)

    for z_layer in bnd_z_layers:
        if z_layer not in img_z_layers:
            raise ValueError(f"There are no images for z-layer {z_layer}")
