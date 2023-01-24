import argparse
import json

import geopandas as gpd
import numpy as np
from shapely.geometry import MultiPolygon

from tests import OUTPUT_FOLDER
from tests.segmentation_utils import assert_df_equals
from vpt.compile_tile_segmentation import run as run_compile_tile_segmentation
from vpt.segmentation.utils.seg_result import SegmentationResult

DATA_PATH = OUTPUT_FOLDER / 'compile_tile_segmentation/'

# todo:
# 1 place json data as a file to test/data folder
# 2 we don't need to clean the test/data/output folder
data_dict = {
    "input_args": {"output_path": DATA_PATH.as_posix()},
    "input_data": {
        "micron_to_mosaic_tform": [
            [2.0, 0.0, 5.0],
            [0.0, 3.0, -4.0],
            [0.0, 0.0, 1.0]
        ]
    },
    "window_grid": {
        "num_tiles": 4,
        "windows": [
            (0, 0, 100, 100),
            (0, 100, 100, 100),
            (100, 0, 100, 100),
            (100, 100, 100, 100)
        ]
    },
    "segmentation_algorithm": {
        "segmentation_task_fusion": {
            "fused_polygon_postprocessing_parameters": {
                "min_final_area": 0,
                "min_distance_between_entities": 2
            }
        },
        "output_files": [
            {
                "entity_types_output": [
                    "cell"
                ],
                "files": {
                    "run_on_tile_dir": "input_dir",
                    "mosaic_geometry_file": "cellpose_mosaic_space.parquet",
                    "micron_geometry_file": "cellpose_micron_space.parquet"
                }
            }
        ]
    }

}


def create_parameters_json():
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH / 'segmentation_specification.json', 'w') as f:
        json.dump(data_dict, f)

    def remove():
        (DATA_PATH / 'segmentation_specification.json').unlink()

    return remove


def create_input():
    (DATA_PATH / 'input_dir').mkdir(parents=True, exist_ok=True)
    gdf = gpd.GeoDataFrame(
        {'ID': [0],
         'EntityID': [0],
         'Name': np.nan,
         'Type': ['Cell'],
         'ParentID': np.nan,
         'ParentType': np.nan,
         'ZLevel': [0.4],
         'ZIndex': [0],
         'geometry': [MultiPolygon([([(75, 75), (125, 75), (125, 125), (75, 125)], [])])]
         })
    gdf.rename_geometry(SegmentationResult.geometry_field, inplace=True)
    gdf.to_parquet(DATA_PATH / 'input_dir' / '0.parquet')

    gdf = gpd.GeoDataFrame(
        {'ID': [1],
         'EntityID': [2],
         'Name': np.nan,
         'Type': ['Cell'],
         'ParentID': np.nan,
         'ParentType': np.nan,
         'ZLevel': [1.5],
         'ZIndex': [1],
         'geometry': [MultiPolygon([([(150, 75), (200, 75), (200, 125), (150, 125)], [])])]
         })
    gdf.rename_geometry(SegmentationResult.geometry_field, inplace=True)
    gdf.to_parquet(DATA_PATH / 'input_dir' / '1.parquet')

    gdf = gpd.GeoDataFrame(
        {'ID': [2],
         'EntityID': [4],
         'Name': np.nan,
         'Type': ['Cell'],
         'ParentID': np.nan,
         'ParentType': np.nan,
         'ZLevel': [1.5],
         'ZIndex': [1],
         'geometry': [MultiPolygon([([(75, 75), (125, 75), (125, 125), (75, 125)], [])])]
         })
    gdf.rename_geometry(SegmentationResult.geometry_field, inplace=True)
    gdf.to_parquet(DATA_PATH / 'input_dir' / '2.parquet')

    gdf = gpd.GeoDataFrame(
        {'ID': [3],
         'EntityID': [3],
         'Name': np.nan,
         'Type': ['Cell'],
         'ParentID': np.nan,
         'ParentType': np.nan,
         'ZLevel': [0.4],
         'ZIndex': [0],
         'geometry': [MultiPolygon([([(100, 100), (130, 100), (130, 200), (100, 200)], [])])]
         })
    gdf.rename_geometry(SegmentationResult.geometry_field, inplace=True)
    gdf.to_parquet(DATA_PATH / 'input_dir' / '3.parquet')

    def remove():
        for i in range(4):
            (DATA_PATH / 'input_dir' / f'{i}.parquet').unlink()

    return remove


def create_output():
    gdf = gpd.GeoDataFrame(
        {'ID': list(range(4)),
         'EntityID': [0, 2, 4, 3],
         'Name': np.nan,
         'Type': ['Cell'] * 4,
         'ParentID': np.nan,
         'ParentType': np.nan,
         'ZLevel': [0.4, 1.5, 1.5, 0.4],
         'ZIndex': [0, 1, 1, 0],
         'geometry': [
             MultiPolygon([([(75, 75), (125, 75), (125, 125), (75, 125)], [])]),
             MultiPolygon([([(150, 75), (200, 75), (200, 125), (150, 125)], [])]),
             MultiPolygon([([(75, 75), (125, 75), (125, 125), (75, 125)], [])]),
             MultiPolygon([([(100, 125), (125, 125), (125, 100), (130, 100), (130, 200), (100, 200)], [])])
         ]})
    gdf.rename_geometry(SegmentationResult.geometry_field, inplace=True)
    return gdf


def test_compile_tile_segmentation():
    remove_parameters_json = create_parameters_json()
    remove_input = create_input()
    expected_gdf = create_output()

    run_compile_tile_segmentation(argparse.Namespace(
        input_segmentation_parameters=f'{(DATA_PATH / "segmentation_specification.json").as_posix()}',
        max_row_group_size=1000, overwrite=True),
    )

    gdf_mosaic = gpd.read_parquet(DATA_PATH / "cellpose_mosaic_space.parquet")
    gdf_micron = gpd.read_parquet(DATA_PATH / "cellpose_micron_space.parquet")

    assert_df_equals(gdf_micron, expected_gdf, 180)

    mosaic_to_micron_tform = np.linalg.inv(data_dict['input_data']['micron_to_mosaic_tform'])
    tform_flat = [*np.array(mosaic_to_micron_tform)[:2, :2].flatten(),
                  *np.array(mosaic_to_micron_tform)[:2, 2].flatten()]

    gdf_mosaic['Geometry'] = gdf_mosaic['Geometry'].affine_transform(tform_flat)

    assert_df_equals(gdf_mosaic, expected_gdf)

    (DATA_PATH / "cellpose_mosaic_space.parquet").unlink()
    (DATA_PATH / "cellpose_micron_space.parquet").unlink()

    remove_parameters_json()
    remove_input()
