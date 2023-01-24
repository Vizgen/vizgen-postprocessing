import json
import os
from contextlib import contextmanager, redirect_stdout, redirect_stderr

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow
import pyarrow.parquet as pq
from geopandas.io.arrow import _geopandas_to_arrow

from vpt.filesystem import filesystem_path_split


MIN_ROW_GROUP_SIZE = 1000


@contextmanager
def suppress_output():
    with open(os.devnull, 'w') as devnull:
        with redirect_stdout(devnull), redirect_stderr(devnull):
            yield


def make_parent_dirs(path):
    fs, path = filesystem_path_split(path)
    parent = fs.sep.join(path.split(fs.sep)[:-1])
    fs.mkdirs(parent, exist_ok=True)


def save_segmentation_results(gdf: gpd.GeoDataFrame, path: str, max_row_group_size=None):
    if max_row_group_size is None:
        save_geodataframe(gdf, path)
    else:
        gdf = gdf.sort_values('EntityID')
        row_group_sizes = derive_row_group_sizes(gdf['EntityID'], max_row_group_size)
        save_geodataframe_with_row_groups(gdf, path, row_group_sizes)


def save_geodataframe(gdf: gpd.GeoDataFrame, path: str) -> None:
    fs, path_inside_fs = filesystem_path_split(path)
    ext = path.split(fs.sep)[-1].split('.')[-1]

    if ext == 'geojson':
        with fs.open(path_inside_fs, 'wb') as f:
            if gdf.empty:
                f.write(json.dumps({"type": "FeatureCollection", "features": []}).encode('utf-8'))
            else:
                gdf.to_file(f, driver='GeoJSON')
    elif ext == 'parquet':
        with fs.open(path_inside_fs, 'wb') as f:
            gdf.to_parquet(f)
    else:
        raise ValueError(f'Unknown file extension: {ext}')


def derive_row_group_sizes(entity_id: pd.Series, max_size: int) -> list[int]:
    assert entity_id.is_monotonic_increasing
    vc = entity_id.value_counts(sort=False)

    group_sizes = []
    curr_group_size = 0

    for i in range(len(vc)):
        if curr_group_size + vc.iloc[i] > max_size:
            group_sizes.append(curr_group_size)
            curr_group_size = 0
        else:
            curr_group_size += vc.iloc[i]

    if curr_group_size > 0:
        group_sizes.append(curr_group_size)

    return group_sizes


def save_geodataframe_with_row_groups(gdf: gpd.GeoDataFrame, path: str,
                                      row_group_sizes: list[int]) -> None:
    fs, path_inside_fs = filesystem_path_split(path)
    ext = path.split(fs.sep)[-1].split('.')[-1]

    assert ext == 'parquet', 'Row groups is a .parquet format specific feature'

    df = gdf.to_wkb()
    schema = _geopandas_to_arrow(gdf).schema

    with fs.open(path_inside_fs, 'wb') as f:
        writer = pq.ParquetWriter(f, schema)

        row_group_offsets = np.concatenate([[0], np.cumsum(row_group_sizes)[:-1]])

        for start, size in zip(row_group_offsets, row_group_sizes):
            row_group = pyarrow.record_batch(df.iloc[start: start + size])
            writer.write_batch(row_group)

        writer.close()
