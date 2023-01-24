import json
import os
from dataclasses import dataclass
from typing import Union, List, Dict, Set

from vpt.filesystem import vzg_open, filesystem_path_split
from vpt.run_segmentation_on_tile.output_utils import make_output_filename
from vpt.segmentation.filters.description import Header
from vpt.segmentation.types import SegTask
from vpt.segmentation.utils.fuse import SegFusion
from vpt.utils.validate import validate_exists, validate_does_not_exist


@dataclass
class InputData:
    image_channel: str
    image_preprocessing: List[Header]

    def __init__(self, image_channel: str, image_preprocessing: List[dict]):
        self.image_channel = image_channel
        self.image_preprocessing = [Header(**x) for x in image_preprocessing]


@dataclass(frozen=True)
class SegProp:
    all_z_indexes: List[int]
    z_positions_um: List[float]


@dataclass(frozen=True)
class ImageInfo:
    channel: str
    z_layer: int
    full_path: Union[str, os.PathLike]


@dataclass(frozen=True)
class SegSpec:
    timestamp: float
    output_paths: Dict[str, str]
    segmentation_tasks: List[SegTask]
    segmentation_task_fusion: SegFusion
    experiment_properties: SegProp
    image_windows: List[List[int]]
    micron_to_mosaic_tform: List[List[float]]
    images: List[ImageInfo]


def validate_micron_to_mosaic_tform(matrix: List[List[float]]):
    if len(matrix) != 3:
        raise ValueError('Micron to mosaic transform matrix should have 3x3 shape')
    for row in matrix:
        if len(row) != 3:
            raise ValueError('Micron to mosaic transform matrix should have 3x3 shape')


def validate_output_path(path: Union[str, os.PathLike], check_empty=True):
    if check_empty:
        validate_does_not_exist(path)


def validate_task(task_data: SegTask, channels: Set[str], z: Set[int]):
    if not set(task_data.z_layers).issubset(z):
        raise ValueError('The segmentation task contains invalid values of the z plane')
    for image_info in task_data.task_input_data:
        if image_info.image_channel not in channels:
            raise ValueError('The segmentation task contains invalid values of the image channel')


def validate_seg_spec(seg_spec: SegSpec, tile_index: int, overwrite_files=False):
    for output_directory in seg_spec.output_paths.values():
        fs, _ = filesystem_path_split(output_directory)
        output_file = fs.sep.join([output_directory, make_output_filename(tile_index)])
        validate_output_path(output_file, not overwrite_files)

    z, channels = set(), set()
    z_chanel = set()
    for image_info in seg_spec.images:
        validate_exists(image_info.full_path)
        if (image_info.z_layer, image_info.channel) in z_chanel:
            raise ValueError('Several images are associated with the same z_plane and channel')
        z_chanel.add((image_info.z_layer, image_info.channel))
        z.add(image_info.z_layer)
        channels.add(image_info.channel)

    validate_micron_to_mosaic_tform(seg_spec.micron_to_mosaic_tform)
    if not set(seg_spec.experiment_properties.all_z_indexes).issuperset(z):
        raise ValueError('Experiment_properties all_z_indexes does not contain all tasks z_planes')
    for task in seg_spec.segmentation_tasks:
        validate_task(task, channels, z)


def create_seg_task(**kwargs):
    data = dict(**kwargs)
    data['task_input_data'] = [InputData(**input_info) for input_info in kwargs['task_input_data']]
    data['entity_types_detected'] = data['entity_types_detected'][0]
    return SegTask(**data)


def get_output_directory_dict(output_files: List[Dict]):
    result = {}
    for output_info in output_files:
        for entity_name in output_info['entity_types_output']:
            result[entity_name] = output_info['files']['run_on_tile_dir']
    return result


def dict_to_segmentation_specification(data: dict) -> SegSpec:
    output_root = data['input_args']['output_path']

    output_fs, _ = filesystem_path_split(output_root)
    rel_output_dict = get_output_directory_dict(data['segmentation_algorithm']['output_files'])

    seg_spec_dict = {
        'timestamp': data['timestamp'],
        'output_paths': {etype: output_fs.sep.join([output_root, path]) for etype, path in rel_output_dict.items()},
        'micron_to_mosaic_tform': data['input_data']['micron_to_mosaic_tform'],
        'images': [ImageInfo(**info) for info in data['input_data']['images']],
        'image_windows': data['window_grid']['windows'],
        'segmentation_tasks': [create_seg_task(**task) for task in
                               data['segmentation_algorithm']['segmentation_tasks']],
        'segmentation_task_fusion': SegFusion(**data['segmentation_algorithm']['segmentation_task_fusion']),
        'experiment_properties': SegProp(**data['segmentation_algorithm']['experiment_properties'])
    }
    return SegSpec(**seg_spec_dict)


def read_seg_spec(json_path: Union[str, os.PathLike], overwrite_files=False) -> SegSpec:
    with vzg_open(str(json_path), 'r') as f:
        data = json.load(f)
    try:
        return dict_to_segmentation_specification(data)
    except AttributeError:
        raise ValueError('Incorrect segmentation specification json')
