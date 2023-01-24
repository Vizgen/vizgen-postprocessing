import argparse
import csv
from typing import List

from vpt import log
from vpt.convert_geometry.cmd_args import ConvertGeometryArgs, validate_cmd_args, parse_cmd_args, \
    validate_args_with_input
from vpt.convert_geometry.factory import read_segmentation_result
from vpt.filesystem import vzg_open, initialize_filesystem
from vpt.filesystem.vzgfs import protocol_path_split, filesystem_for_protocol, prefix_for_protocol
from vpt.segmentation.utils.fuse import SegFusion, fuse_task_polygons
from vpt.segmentation.utils.seg_result import SegmentationResult
from vpt.utils.output_tools import save_segmentation_results
from vpt.utils.regex_tools import get_paths_by_regex
from vpt.utils.validate import validate_exists


def convert_geometry(args: argparse.Namespace):
    convert_args = ConvertGeometryArgs(**vars(args))
    validate_cmd_args(convert_args)

    log.info('Convert geometry started')

    boundaries_paths = get_paths_by_regex(convert_args.input_boundaries)
    for input_path in boundaries_paths:
        validate_args_with_input(convert_args, input_path)

    log.info(f'Found {len(boundaries_paths)} files to process')

    segmentations = []
    map_data = []
    protocol, regex = protocol_path_split(convert_args.input_boundaries)
    _ = filesystem_for_protocol(protocol)
    prefix = prefix_for_protocol(protocol)

    additional_args = {
        'z_planes_number': convert_args.number_z_planes,
        'spacing': convert_args.spacing_z_planes
    } if convert_args.convert_to_3D else {}

    for boundaries_path in log.show_progress(boundaries_paths):
        boundaries_path = ''.join([prefix, boundaries_path])
        validate_exists(boundaries_path)
        seg, ids_map = read_segmentation_result(boundaries_path, entity_type=convert_args.output_entity_type,
                                                **additional_args)
        segmentations.append(seg)
        map_data.extend([boundaries_path, key, val] for key, val in ids_map.items())

    save_ids_map_csv(convert_args.id_mapping_file, map_data)
    fusion_parameters = SegFusion(entity_fusion_strategy=convert_args.entity_fusion_strategy)
    seg_res = fuse_task_polygons(segmentations, fusion_parameters)
    seg_res = SegmentationResult.combine_segmentations(seg_res)

    save_parquet(seg_res, convert_args.output_boundaries, convert_args.max_row_group_size)
    log.info('Convert geometry finished')


def save_parquet(seg_res: SegmentationResult, output_path: str, max_grow_group_size: int):
    if not output_path.endswith('.parquet'):
        output_path = f'{output_path}.parquet'
    gdf = seg_res.df
    save_segmentation_results(gdf, output_path, max_grow_group_size)


def save_ids_map_csv(output_path: str, data: List[List]):
    header = ['SourceFilePath', 'SourceID', 'EntityID']
    if not output_path:
        return
    with vzg_open(output_path, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in data:
            writer.writerow(row)


if __name__ == '__main__':
    initialize_filesystem()
    convert_geometry(parse_cmd_args())
