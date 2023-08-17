import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Union, Tuple

from vpt_core.io.image import ImageInfo
from vpt_core.io.vzgfs import filesystem_path_split, io_with_retries
from vpt_core.segmentation.fuse import SegFusion
from vpt_core.segmentation.segmentation_task import SegTask
from vpt_core.segmentation.task_input_data import InputData

from vpt.prepare_segmentation.validate import validate_fusion_parameters
from vpt.entity.relationships import EntityRelationships, relationships_from_dict, get_default_relationship
from vpt.run_segmentation_on_tile.output_utils import make_entity_output_filename
from vpt.utils.validate import validate_does_not_exist, validate_exists, validate_experimental


@dataclass(frozen=True)
class SegProp:
    all_z_indexes: List[int]
    z_positions_um: List[float]


@dataclass(frozen=True)
class SegSpec:
    timestamp: float
    output_paths: Dict[str, str]
    segmentation_tasks: List[SegTask]
    segmentation_task_fusion: Dict[str, SegFusion]
    entity_type_relationships: Optional[EntityRelationships]
    experiment_properties: SegProp
    image_windows: List[Tuple[int, int, int, int]]
    micron_to_mosaic_tform: List[List[float]]
    images: List[ImageInfo]


def validate_micron_to_mosaic_tform(matrix: List[List[float]]):
    if len(matrix) != 3:
        raise ValueError("Micron to mosaic transform matrix should have 3x3 shape")
    for row in matrix:
        if len(row) != 3:
            raise ValueError("Micron to mosaic transform matrix should have 3x3 shape")


def validate_output_path(path: Union[str, os.PathLike], check_empty=True):
    if check_empty:
        validate_does_not_exist(str(path))


def validate_task(task_data: SegTask, channels: Set[str], z: Set[int]):
    if not set(task_data.z_layers).issubset(z):
        raise ValueError("The segmentation task contains invalid values of the z plane")
    for image_info in task_data.task_input_data:
        if image_info.image_channel not in channels:
            raise ValueError("The segmentation task contains invalid values of the image channel")
    if len(task_data.entity_types_detected) > 1:
        validate_experimental()


def validate_seg_spec(seg_spec: SegSpec, tile_index: int, overwrite_files=False):
    if len(seg_spec.output_paths.keys()) > 1:
        validate_experimental()
    for entity_type, output_directory in seg_spec.output_paths.items():
        fs, _ = filesystem_path_split(output_directory)
        output_file = fs.sep.join([output_directory, make_entity_output_filename(tile_index, entity_type)])
        validate_output_path(output_file, not overwrite_files)

    z, channels = set(), set()
    z_chanel = set()
    for image_info in seg_spec.images:
        validate_exists(str(image_info.full_path))
        if (image_info.z_layer, image_info.channel) in z_chanel:
            raise ValueError("Several images are associated with the same z_plane and channel")
        z_chanel.add((image_info.z_layer, image_info.channel))
        z.add(image_info.z_layer)
        channels.add(image_info.channel)

    validate_micron_to_mosaic_tform(seg_spec.micron_to_mosaic_tform)
    if not set(seg_spec.experiment_properties.all_z_indexes).issuperset(z):
        raise ValueError("Experiment_properties all_z_indexes does not contain all tasks z_planes")
    for task in seg_spec.segmentation_tasks:
        validate_task(task, channels, z)


def create_seg_task(**kwargs) -> SegTask:
    data = dict(**kwargs)
    data["task_input_data"] = [InputData(**input_info) for input_info in kwargs["task_input_data"]]
    data["entity_types_detected"] = [entity_type.lower() for entity_type in data["entity_types_detected"]]
    return SegTask(**data)


def create_seg_fusion(data: Dict) -> Dict[str, SegFusion]:
    fusion_data = data["segmentation_task_fusion"]
    output_entities = [
        entity.lower() for output_info in data["output_files"] for entity in output_info["entity_types_output"]
    ]
    if isinstance(fusion_data, dict):
        validate_fusion_parameters(fusion_data)
        return {entity: SegFusion(**fusion_data) for entity in output_entities}
    else:
        for fusion in fusion_data:
            validate_fusion_parameters(fusion)
        return {entity: SegFusion(**fusion_data[i]) for i, entity in enumerate(output_entities)}


def create_seg_et_relationships(data: dict) -> Optional[EntityRelationships]:
    et_rel_data = data.get("entity_type_relationships", None)
    if not et_rel_data:
        entity_types_output: List[str] = [
            entity_type.lower()
            for output_item in data["output_files"]
            for entity_type in output_item["entity_types_output"]
        ]
        if len(entity_types_output) == 1:
            return None
        else:
            validate_experimental()
            return get_default_relationship()
    validate_experimental()
    return relationships_from_dict(et_rel_data)


def get_output_directory_dict(output_files: List[Dict]):
    result = {}
    for output_info in output_files:
        for entity_name in output_info["entity_types_output"]:
            result[entity_name] = output_info["files"]["run_on_tile_dir"]
    return result


def dict_to_segmentation_specification(data: dict) -> SegSpec:
    output_root = data["input_args"]["output_path"]

    output_fs, _ = filesystem_path_split(output_root)
    rel_output_dict = get_output_directory_dict(data["segmentation_algorithm"]["output_files"])

    seg_spec_dict = {
        "timestamp": data["timestamp"],
        "output_paths": {
            etype.lower(): output_fs.sep.join([output_root, path]) for etype, path in rel_output_dict.items()
        },
        "micron_to_mosaic_tform": data["input_data"]["micron_to_mosaic_tform"],
        "images": [ImageInfo(**info) for info in data["input_data"]["images"]],
        "image_windows": tuple(data["window_grid"]["windows"]),
        "segmentation_tasks": [
            create_seg_task(**task) for task in data["segmentation_algorithm"]["segmentation_tasks"]
        ],
        "segmentation_task_fusion": create_seg_fusion(data["segmentation_algorithm"]),
        "entity_type_relationships": create_seg_et_relationships(data["segmentation_algorithm"]),
        "experiment_properties": SegProp(**data["segmentation_algorithm"]["experiment_properties"]),
    }
    return SegSpec(**seg_spec_dict)


def read_seg_spec(json_path: Union[str, os.PathLike], overwrite_files=False) -> SegSpec:
    data = io_with_retries(str(json_path), "r", json.load)
    try:
        return dict_to_segmentation_specification(data)
    except AttributeError:
        raise ValueError("Incorrect segmentation specification json")
