import json
from dataclasses import dataclass
from typing import List, Dict, Set

from vpt.filesystem.vzgfs import vzg_open


@dataclass(frozen=True)
class OutputFiles:
    run_on_tile_dir: str
    mosaic_geometry_file: str
    micron_geometry_file: str
    cell_metadata_file: str


@dataclass(frozen=True)
class AlgInfo:
    raw: Dict
    stains: Set[str]
    z_layers: Set[int]
    output_files: List[OutputFiles]


def get_stain_set(alg_raw: Dict) -> Set[str]:
    stains = set()

    for task in alg_raw['segmentation_tasks']:
        for data_instance in task['task_input_data']:
            stains.add(data_instance['image_channel'])

    return stains


def get_z_layers_set(alg_raw: Dict) -> Set[int]:
    layers = set()

    for task in alg_raw['segmentation_tasks']:
        layers |= set(task['z_layers'])

    return layers


def get_output_files(alg_raw: Dict) -> List[OutputFiles]:
    return [OutputFiles(**files['files']) for files in alg_raw['output_files']]


def read_algorithm_json(path: str) -> Dict:
    with vzg_open(path, 'r') as f:
        data = json.load(f)
    return data


def parse_algorithm_json(algorithm_json: Dict) -> AlgInfo:
    stains = get_stain_set(algorithm_json)
    z_layers = get_z_layers_set(algorithm_json)
    output_files = get_output_files(algorithm_json)

    return AlgInfo(raw=algorithm_json, stains=stains, z_layers=z_layers, output_files=output_files)
