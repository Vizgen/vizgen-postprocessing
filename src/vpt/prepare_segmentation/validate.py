from typing import List

from vpt.entity.empty_resolver import EmptyResolver
from vpt.entity.factory import get_constraint_resolver
from vpt.entity.relationships import relationships_from_dict
from vpt_core.io.regex_tools import RegexInfo
from vpt_core.io.vzgfs import filesystem_path_split
from vpt_core.segmentation.fuse import FusionCallbacks
from vpt_core.segmentation.seg_result import SegmentationResult

from vpt.prepare_segmentation.input_tools import AlgInfo, OutputFiles
from vpt.segmentation.segmentations_factory import get_seg_implementation
from vpt.utils.validate import validate_directory_empty, validate_does_not_exist, validate_experimental


def validate_regex_and_alg_match(regex_info: RegexInfo, alg_info: AlgInfo):
    parsed_z = set(image.z_layer for image in regex_info.images)
    if not parsed_z.issuperset(alg_info.z_layers):
        raise ValueError(
            f"Z planes from algorithm specification {alg_info.z_layers} do not match "
            f"z planes extracted from regular expression {parsed_z}"
        )
    parsed_stain = set(image.channel for image in regex_info.images)
    if not parsed_stain.issuperset(alg_info.stains):
        raise ValueError(
            f"Stains from algorithm specification {alg_info.stains} do not match "
            f"stains from the regular expression{parsed_stain}"
        )


def validate_output_files_do_not_exist(output_root: str, output_files: List[OutputFiles]):
    output_fs, _ = filesystem_path_split(output_root)

    for files in output_files:
        for file in (files.cell_metadata_file, files.micron_geometry_file, files.mosaic_geometry_file):
            validate_does_not_exist(output_fs.sep.join([output_root, file]))

        validate_directory_empty(output_fs.sep.join([output_root, files.run_on_tile_dir]))


def validate_fusion_parameters(fusion_data: dict):
    if fusion_data["fused_polygon_postprocessing_parameters"]["min_distance_between_entities"] <= 0:
        raise ValueError("Minimal distance between entities should be more than 0")
    if fusion_data["entity_fusion_strategy"].upper() not in FusionCallbacks.__members__:
        raise ValueError("Invalid fusion strategy")


def validate_alg_info(alg_info: AlgInfo, output_path: str, overwrite: bool) -> AlgInfo:
    alg_dict = dict(alg_info.raw)
    if len(alg_dict["segmentation_tasks"]) > SegmentationResult.MAX_TASK_ID:
        raise OverflowError(f"More than {SegmentationResult.MAX_TASK_ID} tasks could not be specified")

    entity_types_output: List[str] = []
    for output_item in alg_dict["output_files"]:
        entity_types_output.extend(entity_type.lower() for entity_type in output_item["entity_types_output"])
    entity_types_output_set = set(entity_types_output)

    if len(entity_types_output) != len(entity_types_output_set):
        raise ValueError(
            "Invalid segmentation algorithm: the entity_types_output lists consists of non-unique elements"
        )
    if len(entity_types_output) > 2:
        raise ValueError("More than two entity types is not supported")
    if len(entity_types_output) > 1:
        validate_experimental()

    for i, task in enumerate(alg_dict["segmentation_tasks"]):
        if not entity_types_output_set.issuperset(entity_type.lower() for entity_type in task["entity_types_detected"]):
            raise ValueError(
                f'Invalid segmentation algorithm: the entity_types_detected list of task {task["task_id"]}'
                " is not a subset of the output entity types"
            )

        if len(task["entity_types_detected"]) != len(set(task["entity_types_detected"])):
            raise ValueError(
                f'Invalid segmentation algorithm: the entity_types_detected list of task {task["task_id"]}'
                " consists of non-unique elements"
            )

        alg_dict["segmentation_tasks"][i] = get_seg_implementation(task["segmentation_family"]).validate_task(task)

    if isinstance(alg_dict["segmentation_task_fusion"], list):
        if len(alg_dict["segmentation_task_fusion"]) != len(entity_types_output):
            raise ValueError(
                "Invalid segmentation algorithm: the length of the list of fusion specifications "
                "is not equal to the number of output entity types"
            )
        for fusion in alg_dict["segmentation_task_fusion"]:
            validate_fusion_parameters(fusion)
    else:
        validate_fusion_parameters(alg_dict["segmentation_task_fusion"])

    if alg_dict.get("entity_type_relationships") is None:
        if not entity_types_output_set.issubset({"cell", "nuclei"}) and len(entity_types_output) > 1:
            raise ValueError("Invalid segmentation algorithm: entity_type_relationships field should be specified")
    else:
        validate_experimental()
        try:
            relationships = relationships_from_dict(alg_dict["entity_type_relationships"])
        except (KeyError, ValueError):
            raise ValueError("Invalid segmentation algorithm: can not parse entity type relationships")

        if len(entity_types_output_set.difference({relationships.child_type, relationships.parent_type})) > 0:
            raise ValueError(
                "Invalid segmentation algorithm: entity_type_relationships types do not match the output entity types"
            )
        for constraint in relationships.constraints:
            try:
                resolver = get_constraint_resolver(constraint, None)
            except ValueError as e:
                raise ValueError(f"Invalid constraint {constraint.constraint}: {e}")

            if isinstance(resolver, EmptyResolver):
                raise ValueError("unknown constraint")

    if not overwrite:
        validate_output_files_do_not_exist(output_path, alg_info.output_files)
    return AlgInfo(alg_dict, alg_info.stains, alg_info.z_layers, alg_info.output_files)
