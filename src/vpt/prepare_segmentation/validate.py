from typing import List

from vpt.filesystem import filesystem_path_split
from vpt.prepare_segmentation.input_tools import AlgInfo, OutputFiles
from vpt.segmentation.factory import get_task_validator
from vpt.segmentation.utils.seg_result import SegmentationResult
from vpt.utils.regex_tools import RegexInfo
from vpt.utils.validate import validate_does_not_exist, validate_directory_empty


def validate_regex_and_alg_match(regex_info: RegexInfo, alg_info: AlgInfo):
    parsed_z = set(image.z_layer for image in regex_info.images)
    if not parsed_z.issuperset(alg_info.z_layers):
        raise ValueError(f'Z planes from algorithm specification {alg_info.z_layers} do not match '
                         f'z planes extracted from regular expression {parsed_z}')
    parsed_stain = set(image.channel for image in regex_info.images)
    if not parsed_stain.issuperset(alg_info.stains):
        raise ValueError(f'Stains from algorithm specification {alg_info.stains} do not match '
                         f'stains from the regular expression{parsed_stain}')


def validate_output_files_do_not_exist(output_root: str, output_files: List[OutputFiles]):
    output_fs, _ = filesystem_path_split(output_root)

    for files in output_files:
        for file in (files.cell_metadata_file,
                     files.micron_geometry_file,
                     files.mosaic_geometry_file):
            validate_does_not_exist(output_fs.sep.join([output_root, file]))

        validate_directory_empty(output_fs.sep.join([output_root, files.run_on_tile_dir]))


# todo: return valid, do not change input
def validate_alg_info(alg_info: AlgInfo, output_path: str, overwrite: bool):
    if len(alg_info.raw['segmentation_tasks']) > SegmentationResult.MAX_TASK_ID:
        raise OverflowError(f'More than {SegmentationResult.MAX_TASK_ID} tasks could not be specified')

    alg_info.raw['segmentation_tasks'] = [get_task_validator(t['segmentation_family'])(t) for t in
                                          alg_info.raw['segmentation_tasks']]

    if not overwrite:
        validate_output_files_do_not_exist(output_path, alg_info.output_files)
