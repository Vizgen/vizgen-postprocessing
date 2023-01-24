from typing import List

import geopandas as gpd

from vpt.filesystem import vzg_open, filesystem_path_split
from vpt.utils.validate import validate_micron_to_mosaic_transform


def read_micron_to_mosaic_transform(path: str) -> List[List[float]]:
    with vzg_open(path, 'r') as f:
        lines = f.readlines()

    def process_line(line: str):
        return list(map(float, line.split()))

    transform = list(map(process_line, lines))

    validate_micron_to_mosaic_transform(transform)

    return transform


def read_geodataframe(path: str):
    fs, path_inside_fs = filesystem_path_split(path)
    ext = path_inside_fs.split(fs.sep)[-1].split('.')[-1]

    if ext == 'parquet':
        with vzg_open(path, 'rb') as f:
            gdf = gpd.read_parquet(f)
    else:
        with vzg_open(path, 'rb') as f:
            gdf = gpd.read_file(f)

    return gdf
