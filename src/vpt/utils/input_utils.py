from typing import List

import geopandas as gpd
from pyarrow import parquet
from shapely import wkb

from vpt_core.io.input_tools import read_parquet
from vpt_core.io.vzgfs import filesystem_path_split, vzg_open, retrying_attempts, io_with_retries
from vpt_core.segmentation.seg_result import SegmentationResult

from vpt.utils.validate import validate_micron_to_mosaic_transform


def read_micron_to_mosaic_transform(path: str) -> List[List[float]]:
    lines = io_with_retries(path, "r", lambda f: f.readlines())

    def process_line(line: str):
        return list(map(float, line.split()))

    transform = list(map(process_line, lines))

    validate_micron_to_mosaic_transform(transform)

    return transform


def read_parquet_by_groups(path: str):
    geom_field = SegmentationResult.geometry_field
    for attempt in retrying_attempts():
        with attempt, vzg_open(path, "rb") as f:
            pq = parquet.ParquetFile(f)
            for i in range(pq.num_row_groups):
                df = gpd.GeoDataFrame(pq.read_row_group(i).to_pandas())
                df[geom_field] = df[geom_field].apply(wkb.loads)
                yield df


def read_geodataframe(path: str):
    fs, path_inside_fs = filesystem_path_split(path)
    ext = path_inside_fs.split(fs.sep)[-1].split(".")[-1]

    if ext == "parquet":
        gdf = read_parquet(path)
    else:
        gdf = io_with_retries(path, "rb", gpd.read_file)

    return gdf


def read_segmentation_entity_types(path: str):
    gdf = read_parquet(path)
    return "_".join(gdf[SegmentationResult.entity_name_field].unique())
