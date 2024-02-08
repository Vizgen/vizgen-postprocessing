from typing import Dict, List

import numpy as np
import pandas as pd

from vpt_core.io.output_tools import format_experiment_timestamp
from vpt_core.io.vzgfs import filesystem_path_split, io_with_retries
from vpt_core.segmentation.seg_result import SegmentationResult


def make_output_filename(tile_index: int) -> str:
    return f"{tile_index}.parquet"


def make_entity_output_filename(tile_index: int, entity_type: str) -> str:
    return f"{entity_type}_{tile_index}.parquet"


def get_entity_type_code(entity_type_name: str) -> int:
    type_codes = {"cell": 100, "cells": 100, "nuclei": 200, "nucleus": 200}
    code = type_codes.get(entity_type_name)
    if code is None:
        # type code for undefined entity type
        return 300
    return code


def update_entity_id(old_id: int, tile: str, time: str, entity_type: int):
    err_m = "Entity id can not be constructed"
    if pd.isnull(old_id):
        return old_id
    if old_id > (1e7 - 1) or old_id < 1e5:
        raise ValueError(f"{err_m}: segmented entity has id = {old_id} with more than 6 digits")
    if len(time) != 8:
        raise ValueError(f"{err_m}: timestamp should have 8 digits")
    if entity_type > 1e5:
        raise ValueError(f"{err_m}: entity type code could not be greater than {1e5}")

    seconds = int(time[-5:])
    old_id_fill = len(str(SegmentationResult.MAX_TASK_ID)) + len(str(SegmentationResult.MAX_ENTITY_ID))
    return np.int64(f"{time[:-5]}{str(seconds + entity_type)}{tile}{str(old_id).zfill(old_id_fill)}")


def save_to_parquet(
    results: List[SegmentationResult],
    tile_id: int,
    timestamp: float,
    z_positions_um: List[float],
    output_paths: Dict[str, str],
):
    tile_id_len = len(str(SegmentationResult.MAX_TILE_ID))
    tile_id_str = str(tile_id).zfill(tile_id_len)

    timestamp_str = format_experiment_timestamp(timestamp)

    for i in range(len(results)):
        results[i].set_column(SegmentationResult.entity_name_field, results[i].entity_type)
        results[i].update_column(
            SegmentationResult.cell_id_field,
            update_entity_id,
            tile=tile_id_str,
            time=timestamp_str,
            entity_type=get_entity_type_code(results[i].entity_type),
        )
        parent_types = results[i].df[SegmentationResult.parent_entity_field].dropna().unique()
        if len(parent_types) > 0:
            results[i].update_column(
                SegmentationResult.parent_id_field,
                update_entity_id,
                tile=tile_id_str,
                time=timestamp_str,
                entity_type=get_entity_type_code(parent_types[0]),
            )

    dataframes: Dict[str, List[SegmentationResult]] = {}
    set_none = ["Name"]
    if z_positions_um is None:
        set_none.append("ZLevel")
    else:
        for i in range(len(results)):
            results[i].set_z_levels(z_positions_um, "ZLevel")
    for entity_type, output_dir in output_paths.items():
        data = SegmentationResult.combine_segmentations([seg for seg in results if seg.entity_type == entity_type])
        data.set_entity_type(entity_type)
        for column_name in set_none:
            data.set_column(column_name, None)
        if not dataframes.get(output_dir):
            dataframes[output_dir] = []
        dataframes[output_dir].append(data)

    for output_dir, dir_results in dataframes.items():
        fs, output_dir_inside_fs = filesystem_path_split(output_dir)
        fs.mkdirs(output_dir_inside_fs, exist_ok=True)
        for entity_results in dir_results:
            if not entity_results.df[entity_results.parent_id_field].isna().all():
                entity_results.df[entity_results.parent_id_field] = entity_results.df[
                    entity_results.parent_id_field
                ].astype("Int64")

            io_with_retries(
                uri=f"{output_dir}/{make_entity_output_filename(tile_id, entity_results.entity_type)}",
                mode="wb",
                callback=entity_results.df.to_parquet,
            )
