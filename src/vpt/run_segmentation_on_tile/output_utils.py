from datetime import datetime
from typing import List, Dict

import geopandas
import pandas as pd
import numpy as np

from vpt.filesystem import vzg_open, filesystem_path_split
from vpt.segmentation.utils.seg_result import SegmentationResult


def make_output_filename(tile_index: int) -> str:
    return f'{tile_index}.parquet'


def get_entity_type_code(entity_type_name: str) -> int:
    type_codes = {'cell': 100, 'cells': 100, 'nuclei': 200, 'nucleus': 200}
    code = type_codes.get(entity_type_name)
    if code is None:
        # type code for undefined entity type
        return 300
    return code


def update_entity_id(old_id: int, tile: str, time: str, entity_type: int):
    err_m = 'Entity id can not be constructed'
    if old_id > (1e7 - 1) or old_id < 1e5:
        raise ValueError(f'{err_m}: segmented entity has id = {old_id} with more than 6 digits')
    if len(time) != 8:
        raise ValueError(f'{err_m}: timestamp should have 8 digits')
    if entity_type > 1e5:
        raise ValueError(f'{err_m}: entity type code could not be greater than {1e5}')

    seconds = int(time[-5:])
    old_id_fill = len(str(SegmentationResult.MAX_TASK_ID)) + len(str(SegmentationResult.MAX_ENTITY_ID))
    return np.int64(f'{time[:-5]}{str(seconds + entity_type)}{tile}{str(old_id).zfill(old_id_fill)}')


def save_to_parquet(results: List[SegmentationResult], tile_id: int, timestamp: float, z_positions_um: List[float],
                    output_paths: Dict[str, str]):
    tile_id_len = len(str(SegmentationResult.MAX_TILE_ID))
    tile_id_str = str(tile_id).zfill(tile_id_len)

    year_day = str(int(datetime.fromtimestamp(timestamp).strftime('%j')) + 100)
    day_time = datetime.fromtimestamp(timestamp).strftime('%H%M%S')
    day_second = str(int(day_time[:2]) * 60 ** 2 + int(day_time[2:4]) * 60 + int(day_time[4:])).zfill(5)
    timestamp_str = ''.join([year_day, day_second])

    for i in range(len(results)):
        results[i].set_column(SegmentationResult.entity_name_field, results[i].entity_type)
        results[i].update_column(SegmentationResult.cell_id_field, update_entity_id, tile=tile_id_str,
                                 time=timestamp_str, entity_type=get_entity_type_code(results[i].entity_type))

    dataframes = {}
    set_none = ['Name', 'ParentID', 'ParentType']
    if z_positions_um is None:
        set_none.append('ZLevel')
    else:
        for i in range(len(results)):
            results[i].set_z_levels(z_positions_um, 'ZLevel')
    for entity_type, output_dir in output_paths.items():
        data = SegmentationResult.combine_segmentations([seg for seg in results if seg.entity_type == entity_type])
        for column_name in set_none:
            data.set_column(column_name, None)
        if not dataframes.get(output_dir):
            dataframes[output_dir] = []
        dataframes[output_dir].append(data.df)

    for output_dir, dataframe in dataframes.items():
        fs, output_dir_inside_fs = filesystem_path_split(output_dir)
        fs.mkdirs(output_dir_inside_fs, exist_ok=True)

        gdf_compiled = geopandas.GeoDataFrame(pd.concat(dataframe))
        with vzg_open(f'{output_dir}/{make_output_filename(tile_id)}', 'wb') as f:
            gdf_compiled.to_parquet(f)
