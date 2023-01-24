from dataclasses import dataclass
from pathlib import Path
from typing import List

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import MultiPolygon

from tests import OUTPUT_FOLDER
from tests.base_case import BaseCase
from tests.segmentation_utils import assert_df_equals
from vpt.compile_tile_segmentation.main import compile_dataframe
from vpt.compile_tile_segmentation.parameters import CompileParameters
from vpt.filesystem import initialize_filesystem
from vpt.segmentation.utils.seg_result import SegmentationResult

TEMP_DIR = OUTPUT_FOLDER / 'compile_tile_segmentation/test_compile_dataframe/'


@dataclass
class TileFile:
    tile_index: int

    id: List
    entity_id: List
    entity_type: List
    z_level: List
    z_index: List
    geometry: List


class CompileDataFrameCase(BaseCase):

    def __init__(self, name: str, files: List[TileFile],
                 input_dir: str, result: gpd.GeoDataFrame):
        super(CompileDataFrameCase, self).__init__(name)

        self.files = files
        self.input_dir = input_dir
        self.result = result.rename_geometry("Geometry")

    def create_tile_file(self, tile_file: TileFile):
        gdf = gpd.GeoDataFrame({'ID': tile_file.id,
                                'EntityID': tile_file.entity_id,
                                'Name': np.nan,
                                'Type': tile_file.entity_type,
                                'ParentID': np.nan,
                                'ParentType': np.nan,
                                'ZLevel': tile_file.z_level,
                                'ZIndex': tile_file.z_index,
                                'geometry': tile_file.geometry})
        gdf.rename_geometry("Geometry", inplace=True)
        output_path = Path(TEMP_DIR) / self.input_dir / f'{tile_file.tile_index}.parquet'
        Path(output_path.parent).mkdir(exist_ok=True, parents=True)
        gdf.to_parquet(output_path)

    def remove_tile_file(self, tile_file: TileFile):
        (Path(TEMP_DIR) / self.input_dir / f'{tile_file.tile_index}.parquet').unlink()

    def setup(self):
        for tile_file in self.files:
            self.create_tile_file(tile_file)

    def teardown(self):
        for tile_file in self.files:
            self.remove_tile_file(tile_file)


COMPILE_DATAFRAME_CASES = [
    CompileDataFrameCase(
        'random',
        [TileFile(tile_index=0,
                  id=[0, 1],
                  entity_id=[3, 10],
                  entity_type=['Cell'] * 2,
                  z_index=[0, 0],
                  z_level=[0, 0],
                  geometry=[MultiPolygon([([(0, 0), (0, 20), (20, 20), (20, 0)], [])]),
                            MultiPolygon([([(90, 40), (120, 40), (120, 80)], [])])]),
         TileFile(tile_index=1,
                  id=[0, 1],
                  entity_id=[40, 30],
                  entity_type=['Cell'] * 2,
                  z_index=[0, 0],
                  z_level=[0, 0],
                  geometry=[
                      MultiPolygon([([(100, 20), (100, 80), (180, 80), (180, 20)], [])]),
                      MultiPolygon([([(125, 90), (175, 90), (175, 110), (125, 110)], [])])]),
         TileFile(tile_index=2,
                  id=[],
                  entity_id=[],
                  entity_type=[],
                  z_index=[],
                  z_level=[],
                  geometry=[]),
         TileFile(tile_index=3,
                  id=[0],
                  entity_id=[100],
                  entity_type=['Cell'],
                  z_index=[0],
                  z_level=[0],
                  geometry=[MultiPolygon(
                      [([(125, 100), (175, 100), (175, 140), (125, 140)], [])])])],
        'input_dir',
        gpd.GeoDataFrame({'ID': list(range(4)),
                          'EntityID': [3, 40, 30, 100],
                          'Name': np.nan,
                          'Type': ['Cell'] * 4,
                          'ParentID': np.nan,
                          'ParentType': np.nan,
                          'ZLevel': [0] * 4,
                          'ZIndex': [0] * 4,
                          'geometry': [
                              MultiPolygon([([(0, 0), (0, 20), (20, 20), (20, 0)], [])]),
                              MultiPolygon(
                                  [([(100, 20), (100, 40), (90, 40), (100, 53.3), (100, 80), (180, 80), (180, 20)], [])]),
                              MultiPolygon(
                                  [([(125, 90), (175, 90), (175, 110), (125, 110)], [])]),
                              MultiPolygon(
                                  [([(125, 120), (175, 120), (175, 140), (125, 140)], [])])
                          ]})
    )
]


@pytest.mark.parametrize('case', COMPILE_DATAFRAME_CASES, ids=str)
def test_compile_dataframe(case: CompileDataFrameCase) -> None:
    initialize_filesystem()
    case.setup()

    try:
        def adapter(i):
            return SegmentationResult(dataframe=gpd.read_parquet(Path(TEMP_DIR) / case.input_dir / f'{i}.parquet'))
        result = compile_dataframe(adapter, CompileParameters(4, np.eye(3), 2, 10)).df
        assert_df_equals(result, case.result)
    finally:
        case.teardown()


@pytest.mark.parametrize('case', COMPILE_DATAFRAME_CASES, ids=str)
def test_micron_compile_dataframe(case: CompileDataFrameCase) -> None:
    initialize_filesystem()
    case.setup()
    try:
        micron_to_mosaic = np.array([[9.25959014, 0, -125.49], [0, 9.25959014, 121.55], [0, 0, 1]])
        mosaic_to_micron = np.linalg.inv(micron_to_mosaic)

        def adapter(i):
            seg = SegmentationResult(dataframe=gpd.read_parquet(Path(TEMP_DIR) / case.input_dir / f'{i}.parquet'))
            seg.transform_geoms(mosaic_to_micron)
            return seg

        result = compile_dataframe(adapter, CompileParameters(num_tiles=4,
                                                              micron_to_mosaic_matrix=micron_to_mosaic,
                                                              min_final_area=2,
                                                              min_distance=10))
        result.transform_geoms(micron_to_mosaic)
        assert_df_equals(result.df, case.result)
    finally:
        case.teardown()
