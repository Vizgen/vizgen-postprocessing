from dataclasses import dataclass
from typing import Dict, Tuple, Optional

import numpy as np

from vpt.entity.relationships import EntityRelationships
from vpt.utils.seg_spec_utils import create_seg_fusion, create_seg_et_relationships
from vpt_core.io.vzgfs import filesystem_path_split
from vpt_core.segmentation.fuse import PolygonParams


@dataclass
class IOPaths:
    input_dir: str
    mosaic_output_file: str
    micron_output_file: str


@dataclass
class CompileParameters:
    num_tiles: int
    micron_to_mosaic_matrix: np.ndarray
    polygon_parameters: Dict[str, PolygonParams]
    entity_type_relationships: Optional[EntityRelationships]


def extract_parameters_from_spec(spec: Dict) -> Tuple[Dict[str, IOPaths], CompileParameters]:
    output_root = spec["input_args"]["output_path"]
    output_fs, _ = filesystem_path_split(output_root)

    num_tiles = spec["window_grid"]["num_tiles"]

    entity_type_to_paths_mapping = {}
    output_file_groups = spec["segmentation_algorithm"]["output_files"]
    for record in output_file_groups:
        for entity_type in record["entity_types_output"]:
            if len(record["entity_types_output"]) == 1 and len(output_file_groups) == 1:
                io_path = IOPaths(
                    input_dir=output_fs.sep.join([output_root, record["files"]["run_on_tile_dir"]]),
                    mosaic_output_file=output_fs.sep.join([output_root, record["files"]["mosaic_geometry_file"]]),
                    micron_output_file=output_fs.sep.join([output_root, record["files"]["micron_geometry_file"]]),
                )
            else:
                io_path = IOPaths(
                    input_dir=output_fs.sep.join([output_root, record["files"]["run_on_tile_dir"]]),
                    mosaic_output_file=output_fs.sep.join(
                        [output_root, "_".join([entity_type.lower(), record["files"]["mosaic_geometry_file"]])]
                    ),
                    micron_output_file=output_fs.sep.join(
                        [output_root, "_".join([entity_type.lower(), record["files"]["micron_geometry_file"]])]
                    ),
                )
            entity_type_to_paths_mapping[entity_type.lower()] = io_path

    m2m_tform = np.array(spec["input_data"]["micron_to_mosaic_tform"])
    m2m_inv = np.linalg.inv(m2m_tform)
    x_scale, y_scale = m2m_inv[0, 0], m2m_inv[1, 1]
    segmentation_fusion = create_seg_fusion(spec["segmentation_algorithm"])
    micron_polygon_params = {
        entity_type: PolygonParams(
            seg_fusion.fused_polygon_postprocessing_parameters.min_final_area * x_scale * y_scale,
            seg_fusion.fused_polygon_postprocessing_parameters.min_distance_between_entities * x_scale,
        )
        for entity_type, seg_fusion in segmentation_fusion.items()
    }
    entity_type_relationships = create_seg_et_relationships(spec["segmentation_algorithm"])

    return entity_type_to_paths_mapping, CompileParameters(
        num_tiles, m2m_tform, micron_polygon_params, entity_type_relationships
    )
