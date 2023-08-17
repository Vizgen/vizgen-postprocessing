import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Optional

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import MultiPolygon

from vpt.entity.relationships import EntityRelationships
from vpt.run_segmentation_on_tile.output_utils import make_entity_output_filename
from vpt_core.io.input_tools import read_parquet
from vpt_core.segmentation.seg_result import SegmentationResult
from vpt_core.utils.base_case import BaseCase
from vpt_core.utils.segmentation_utils import assert_df_equals, Square, Rect

from tests.vpt import OUTPUT_FOLDER
from vpt.compile_tile_segmentation import run as run_compile_tile_segmentation

DATA_PATH = OUTPUT_FOLDER / "compile_tile_segmentation/"


def relationships_dict_from_object(relationships: EntityRelationships) -> Dict:
    return {
        "parent_type": relationships.parent_type,
        "child_type": relationships.child_type,
        "child_coverage_threshold": relationships.child_coverage_threshold,
        "constraints": [
            {"constraint": constraint.constraint, "value": constraint.value, "resolution": constraint.resolution.value}
            for constraint in relationships.constraints
        ],
    }


def get_segmentation_geodataframe(gdf: gpd.GeoDataFrame):
    return gdf.rename_geometry("Geometry")


# todo:
# 1 place json data as a file to test/data folder
# 2 we don't need to clean the test/data/output folder
def create_data_from_args(
    storage_path: Path,
    tiles_num: int,
    m2m_transform: np.ndarray,
    entities_by_path: Dict[str, List],
    relationships: Optional[EntityRelationships],
    fusion_strategy: str,
    min_distance_between_entities: int,
) -> Dict:
    res = {
        "input_args": {"output_path": storage_path.as_posix()},
        "input_data": {"micron_to_mosaic_tform": m2m_transform.tolist()},
        "window_grid": {
            "num_tiles": tiles_num,
            "windows": [(i, 0, 0, 0) for i in range(tiles_num)],
        },
        "segmentation_algorithm": {
            "segmentation_task_fusion": {
                "fused_polygon_postprocessing_parameters": {
                    "min_final_area": 0,
                    "min_distance_between_entities": min_distance_between_entities,
                },
                "entity_fusion_strategy": fusion_strategy,
            },
            "output_files": [
                {
                    "entity_types_output": entity_types,
                    "files": {
                        "run_on_tile_dir": run_on_tile_dir,
                        "mosaic_geometry_file": "cellpose_mosaic_space.parquet",
                        "micron_geometry_file": "cellpose_micron_space.parquet",
                    },
                }
                for run_on_tile_dir, entity_types in entities_by_path.items()
            ],
        },
    }
    if relationships:
        res["segmentation_algorithm"]["entity_type_relationships"] = relationships_dict_from_object(relationships)
    entities_num = len(set(entity for entities in entities_by_path.values() for entity in entities))
    if entities_num > 1:
        res["segmentation_algorithm"]["segmentation_task_fusion"] = [
            res["segmentation_algorithm"]["segmentation_task_fusion"]
        ] * entities_num
    return res


class TileData:
    def __init__(self, number: int, store_dirs: Dict[str, str], seg_results: List[SegmentationResult]):
        self.number = number
        self.store_dirs = store_dirs
        self.seg_results = seg_results
        for i in range(len(self.seg_results)):
            self.seg_results[i].set_entity_type(self.seg_results[i].df[SegmentationResult.entity_name_field][0])
        self.stored_files: List[Path] = []

    def create_input(self, test_dir):
        for seg_res in self.seg_results:
            output_path = test_dir / self.store_dirs[seg_res.entity_type]
            output_path.mkdir(parents=True, exist_ok=True)

            output_path = output_path / make_entity_output_filename(self.number, seg_res.entity_type)
            seg_res.df.to_parquet(output_path)
            self.stored_files.append(output_path)

    def clear(self):
        for output_path in self.stored_files:
            output_path.unlink()


class CompileTileCase(BaseCase):
    def __init__(
        self,
        name: str,
        input_data: List[TileData],
        result: Dict[str, SegmentationResult],
        relationships: Optional[EntityRelationships] = None,
        m2m_transform: Optional[np.ndarray] = None,
        test_dir: Path = DATA_PATH,
        fusion_strategy: str = "harmonize",
        min_distance_between_entities: int = 2,
    ):
        super(CompileTileCase, self).__init__(name)
        self.input_data = input_data
        self.test_dir = test_dir
        self.result = result
        self.m2m_transform = m2m_transform if m2m_transform is not None else np.identity(3)
        self.relationships = relationships
        self.fusion_strategy = fusion_strategy
        self.min_distance = min_distance_between_entities

        self._seg_spec_data = dict()

    def create_parameters_json(self):
        for tile_info in self.input_data:
            tile_info.create_input(self.test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)
        entities_by_paths = defaultdict(list)
        for tile_info in self.input_data:
            for entity, out_dir in tile_info.store_dirs.items():
                if entity not in entities_by_paths[out_dir]:
                    entities_by_paths[out_dir].append(entity)

        self._seg_spec_data = create_data_from_args(
            self.test_dir,
            len(self.input_data),
            self.m2m_transform,
            entities_by_paths,
            self.relationships,
            self.fusion_strategy,
            self.min_distance,
        )

        with open(self.test_dir / "segmentation_specification.json", "w") as f:
            json.dump(self._seg_spec_data, f)

    def check_run_results(self):
        output_file_groups = self._seg_spec_data["segmentation_algorithm"]["output_files"]
        for result_output_info in output_file_groups:
            for entity_type in result_output_info["entity_types_output"]:
                if len(result_output_info["entity_types_output"]) > 1 or len(output_file_groups) > 1:
                    gdf_mosaic = read_parquet(
                        str(self.test_dir / f"{entity_type}_{result_output_info['files']['mosaic_geometry_file']}")
                    )
                    gdf_micron = read_parquet(
                        str(self.test_dir / f"{entity_type}_{result_output_info['files']['micron_geometry_file']}")
                    )
                else:
                    gdf_mosaic = read_parquet(
                        str(self.test_dir / f"{result_output_info['files']['mosaic_geometry_file']}")
                    )
                    gdf_micron = read_parquet(
                        str(self.test_dir / f"{result_output_info['files']['micron_geometry_file']}")
                    )

                assert len(SegmentationResult.find_overlapping_entities(gdf_micron)) == 0
                assert len(SegmentationResult.find_overlapping_entities(gdf_mosaic)) == 0
                assert_df_equals(gdf_micron, self.result[entity_type].df, 180)

                mosaic_to_micron_tform = np.linalg.inv(self.m2m_transform)
                tform_flat = [
                    *np.array(mosaic_to_micron_tform)[:2, :2].flatten(),
                    *np.array(mosaic_to_micron_tform)[:2, 2].flatten(),
                ]
                gdf_mosaic["Geometry"] = gdf_mosaic["Geometry"].affine_transform(tform_flat)

                assert_df_equals(gdf_mosaic, self.result[entity_type].df)


COMPILE_TILE_CASES = [
    CompileTileCase(
        name="one_entity",
        input_data=[
            TileData(
                number=0,
                store_dirs={"cell": "input_dir"},
                seg_results=[
                    SegmentationResult(
                        dataframe=get_segmentation_geodataframe(
                            gpd.GeoDataFrame(
                                {
                                    "ID": [0],
                                    "EntityID": [0],
                                    "Name": np.nan,
                                    "Type": ["cell"],
                                    "ParentID": np.nan,
                                    "ParentType": np.nan,
                                    "ZLevel": [0.4],
                                    "ZIndex": [0],
                                    "geometry": [MultiPolygon([([(75, 75), (125, 75), (125, 125), (75, 125)], [])])],
                                }
                            )
                        )
                    )
                ],
            ),
            TileData(
                number=1,
                store_dirs={"cell": "input_dir"},
                seg_results=[
                    SegmentationResult(
                        dataframe=get_segmentation_geodataframe(
                            gpd.GeoDataFrame(
                                {
                                    "ID": [1],
                                    "EntityID": [2],
                                    "Name": np.nan,
                                    "Type": ["cell"],
                                    "ParentID": np.nan,
                                    "ParentType": np.nan,
                                    "ZLevel": [1.5],
                                    "ZIndex": [1],
                                    "geometry": [MultiPolygon([([(150, 75), (200, 75), (200, 125), (150, 125)], [])])],
                                }
                            )
                        )
                    )
                ],
            ),
            TileData(
                number=2,
                store_dirs={"cell": "input_dir"},
                seg_results=[
                    SegmentationResult(
                        dataframe=get_segmentation_geodataframe(
                            gpd.GeoDataFrame(
                                {
                                    "ID": [2],
                                    "EntityID": [4],
                                    "Name": np.nan,
                                    "Type": ["cell"],
                                    "ParentID": np.nan,
                                    "ParentType": np.nan,
                                    "ZLevel": [1.5],
                                    "ZIndex": [1],
                                    "geometry": [MultiPolygon([([(75, 75), (125, 75), (125, 125), (75, 125)], [])])],
                                }
                            )
                        )
                    )
                ],
            ),
            TileData(
                number=3,
                store_dirs={"cell": "input_dir"},
                seg_results=[
                    SegmentationResult(
                        dataframe=get_segmentation_geodataframe(
                            gpd.GeoDataFrame(
                                {
                                    "ID": [3],
                                    "EntityID": [3],
                                    "Name": np.nan,
                                    "Type": ["cell"],
                                    "ParentID": np.nan,
                                    "ParentType": np.nan,
                                    "ZLevel": [0.4],
                                    "ZIndex": [0],
                                    "geometry": [
                                        MultiPolygon([([(100, 100), (130, 100), (130, 200), (100, 200)], [])])
                                    ],
                                }
                            )
                        )
                    )
                ],
            ),
        ],
        result={
            "cell": SegmentationResult(
                dataframe=get_segmentation_geodataframe(
                    gpd.GeoDataFrame(
                        {
                            "ID": list(range(4)),
                            "EntityID": [0, 2, 4, 3],
                            "Name": np.nan,
                            "Type": ["cell"] * 4,
                            "ParentID": np.nan,
                            "ParentType": np.nan,
                            "ZLevel": [0.4, 1.5, 1.5, 0.4],
                            "ZIndex": [0, 1, 1, 0],
                            "geometry": [
                                MultiPolygon([([(75, 75), (125, 75), (125, 125), (75, 125)], [])]),
                                MultiPolygon([([(150, 75), (200, 75), (200, 125), (150, 125)], [])]),
                                MultiPolygon([([(75, 75), (125, 75), (125, 125), (75, 125)], [])]),
                                MultiPolygon(
                                    [([(100, 125), (125, 125), (125, 100), (130, 100), (130, 200), (100, 200)], [])]
                                ),
                            ],
                        }
                    )
                )
            )
        },
        m2m_transform=np.array([[2.0, 0.0, 5.0], [0.0, 3.0, -4.0], [0.0, 0.0, 1.0]]),
    ),
    CompileTileCase(
        name="multiple_entities",
        input_data=[
            TileData(
                number=0,
                store_dirs={"cell": "input_cell", "nuclei": "input_nuclei"},
                seg_results=[
                    SegmentationResult(
                        dataframe=get_segmentation_geodataframe(
                            gpd.GeoDataFrame(
                                {
                                    "ID": [0],
                                    "EntityID": [0],
                                    "Name": np.nan,
                                    "Type": ["cell"],
                                    "ParentID": np.nan,
                                    "ParentType": np.nan,
                                    "ZLevel": [0.4],
                                    "ZIndex": [0],
                                    "geometry": [Square(10, 15, 10)],
                                }
                            )
                        )
                    ),
                    SegmentationResult(
                        dataframe=get_segmentation_geodataframe(
                            gpd.GeoDataFrame(
                                {
                                    "ID": [0],
                                    "EntityID": [1],
                                    "Name": np.nan,
                                    "Type": ["nuclei"],
                                    "ParentID": [0],
                                    "ParentType": ["cell"],
                                    "ZLevel": [0.4],
                                    "ZIndex": [0],
                                    "geometry": [Rect(10, 15, 7.5, 10)],
                                }
                            )
                        )
                    ),
                ],
            ),
            TileData(
                number=1,
                store_dirs={"cell": "input_cell", "nuclei": "input_nuclei"},
                seg_results=[
                    SegmentationResult(
                        dataframe=get_segmentation_geodataframe(
                            gpd.GeoDataFrame(
                                {
                                    "ID": [0],
                                    "EntityID": [2],
                                    "Name": np.nan,
                                    "Type": ["cell"],
                                    "ParentID": np.nan,
                                    "ParentType": np.nan,
                                    "ZLevel": [0.4],
                                    "ZIndex": [0],
                                    "geometry": [Rect(5, 12.5, 15, 5)],
                                }
                            )
                        )
                    ),
                    SegmentationResult(
                        dataframe=get_segmentation_geodataframe(
                            gpd.GeoDataFrame(
                                {
                                    "ID": [0],
                                    "EntityID": [3],
                                    "Name": np.nan,
                                    "Type": ["nuclei"],
                                    "ParentID": [2],
                                    "ParentType": ["cell"],
                                    "ZLevel": [0.4],
                                    "ZIndex": [0],
                                    "geometry": [Rect(7.5, 12.5, 10, 5)],
                                }
                            )
                        )
                    ),
                ],
            ),
        ],
        result={
            "cell": SegmentationResult(
                dataframe=get_segmentation_geodataframe(
                    gpd.GeoDataFrame(
                        {
                            "ID": [0, 1],
                            "EntityID": [0, 2],
                            "Name": np.nan,
                            "Type": ["cell"] * 2,
                            "ParentID": np.nan,
                            "ParentType": np.nan,
                            "ZLevel": [0.4] * 2,
                            "ZIndex": [0] * 2,
                            "geometry": [Rect(10, 17.5, 10, 7.5), Rect(5, 12.5, 15, 5)],
                        }
                    )
                )
            ),
            "nuclei": SegmentationResult(
                dataframe=get_segmentation_geodataframe(
                    gpd.GeoDataFrame(
                        {
                            "ID": [0, 1],
                            "EntityID": [1, 3],
                            "Name": np.nan,
                            "Type": ["nuclei"] * 2,
                            "ParentID": [0, 2],
                            "ParentType": ["cell"] * 2,
                            "ZLevel": [0.4] * 2,
                            "ZIndex": [0] * 2,
                            "geometry": [Square(10, 17.5, 7.5), Rect(7.5, 12.5, 10, 5)],
                        }
                    )
                )
            ),
        },
    ),
]

INVALID_COMPILE_TILE_CASES = [
    CompileTileCase(
        name="invalid distance",
        input_data=[],
        result={},
        m2m_transform=np.array([[2.0, 0.0, 5.0], [0.0, 3.0, -4.0], [0.0, 0.0, 1.0]]),
        min_distance_between_entities=0,
    ),
    CompileTileCase(
        name="invalid strategy",
        input_data=[],
        result={},
        m2m_transform=np.array([[2.0, 0.0, 5.0], [0.0, 3.0, -4.0], [0.0, 0.0, 1.0]]),
        fusion_strategy="invalid",
    ),
]


@pytest.mark.parametrize("case", COMPILE_TILE_CASES, ids=str)
def test_compile_tile_segmentation(case: CompileTileCase):
    case.create_parameters_json()
    run_compile_tile_segmentation(
        argparse.Namespace(
            input_segmentation_parameters=f'{(case.test_dir / "segmentation_specification.json").as_posix()}',
            max_row_group_size=1000,
            overwrite=True,
        ),
    )
    case.check_run_results()


@pytest.mark.parametrize("case", INVALID_COMPILE_TILE_CASES, ids=str)
def test_invalid_spec(case: CompileTileCase):
    case.create_parameters_json()
    with pytest.raises(ValueError):
        run_compile_tile_segmentation(
            argparse.Namespace(
                input_segmentation_parameters=f'{(case.test_dir / "segmentation_specification.json").as_posix()}',
                max_row_group_size=1000,
                overwrite=True,
            ),
        )
