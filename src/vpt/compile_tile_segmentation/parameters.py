from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np

from vpt.filesystem.vzgfs import filesystem_path_split


@dataclass
class IOPaths:
    input_dir: str
    mosaic_output_file: str
    micron_output_file: str


@dataclass
class CompileParameters:
    num_tiles: int
    micron_to_mosaic_matrix: np.ndarray
    min_final_area: int
    min_distance: int


def extract_parameters_from_spec(spec: Dict) -> Tuple[Dict[str, IOPaths], CompileParameters]:
    output_root = spec['input_args']['output_path']
    output_fs, _ = filesystem_path_split(output_root)

    num_tiles = spec['window_grid']['num_tiles']

    entity_type_to_paths_mapping = {
        entity_type: IOPaths(input_dir=output_fs.sep.join([output_root, record['files']['run_on_tile_dir']]),
                             mosaic_output_file=output_fs.sep.join(
                                 [output_root, record['files']['mosaic_geometry_file']]),
                             micron_output_file=output_fs.sep.join(
                                 [output_root, record['files']['micron_geometry_file']]))
        for record in spec['segmentation_algorithm']['output_files'] for entity_type in record['entity_types_output']
    }
    m2m_tform = np.array(spec['input_data']['micron_to_mosaic_tform'])
    polys_postprocessing = spec['segmentation_algorithm']['segmentation_task_fusion']
    polys_postprocessing = polys_postprocessing['fused_polygon_postprocessing_parameters']
    min_area = polys_postprocessing['min_final_area']
    min_distance = polys_postprocessing['min_distance_between_entities']

    return entity_type_to_paths_mapping, CompileParameters(num_tiles, m2m_tform, min_area, min_distance)
