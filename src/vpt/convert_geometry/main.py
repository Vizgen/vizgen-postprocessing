import argparse
import csv
from typing import List

import numpy as np
from vpt_core import log
from vpt_core.io.output_tools import save_segmentation_results
from vpt_core.io.regex_tools import get_paths_by_regex
from vpt_core.io.vzgfs import (
    filesystem_for_protocol,
    initialize_filesystem,
    prefix_for_protocol,
    protocol_path_split,
    vzg_open,
    retrying_attempts,
)
from vpt_core.segmentation.fuse import SegFusion, fuse_task_polygons
from vpt_core.segmentation.seg_result import SegmentationResult

from vpt.convert_geometry.cmd_args import (
    ConvertGeometryArgs,
    parse_cmd_args,
    validate_args_with_input,
    validate_cmd_args,
)
from vpt.convert_geometry.factory import read_segmentation_result
from vpt.utils.input_utils import read_micron_to_mosaic_transform
from vpt.utils.validate import validate_exists


def convert_geometry(args: argparse.Namespace):
    convert_args = ConvertGeometryArgs(**vars(args))
    validate_cmd_args(convert_args)

    log.info("Convert geometry started")

    boundaries_paths = get_paths_by_regex(convert_args.input_boundaries)
    for input_path in boundaries_paths:
        validate_args_with_input(convert_args, input_path)

    log.info(f"Found {len(boundaries_paths)} files to process")

    segmentations = []
    map_data: List = []
    protocol, regex = protocol_path_split(convert_args.input_boundaries)
    _ = filesystem_for_protocol(protocol)
    prefix = prefix_for_protocol(protocol)

    additional_args = (
        {"z_planes_number": convert_args.number_z_planes, "spacing": convert_args.spacing_z_planes}
        if convert_args.convert_to_3D
        else {}
    )

    for boundaries_path in log.show_progress(boundaries_paths):
        boundaries_path = "".join([prefix, boundaries_path])
        validate_exists(boundaries_path)
        seg, ids_map = read_segmentation_result(
            boundaries_path, entity_type=convert_args.output_entity_type, **additional_args
        )
        segmentations.append(seg)
        map_data.extend([boundaries_path, key, val] for key, val in ids_map.items())

    save_ids_map_csv(convert_args.id_mapping_file, map_data)
    fusion_parameters = {
        convert_args.output_entity_type: SegFusion(entity_fusion_strategy=convert_args.entity_fusion_strategy)
    }
    seg_res = fuse_task_polygons(segmentations, fusion_parameters)
    seg_res = SegmentationResult.combine_segmentations(seg_res)
    if convert_args.input_micron_to_mosaic:
        log.info("Transformation")
        micron_to_mosaic = read_micron_to_mosaic_transform(convert_args.input_micron_to_mosaic)
        mosaic_to_micron_matrix = np.linalg.inv(micron_to_mosaic)
        seg_res.transform_geoms(mosaic_to_micron_matrix)
        log.info("Mosaic-to-micron transformation finished!")

    save_parquet(seg_res, convert_args.output_boundaries, convert_args.max_row_group_size)
    log.info("Convert geometry finished")


def save_parquet(seg_res: SegmentationResult, output_path: str, max_grow_group_size: int):
    if not output_path.endswith(".parquet"):
        output_path = f"{output_path}.parquet"
    gdf = seg_res.df
    save_segmentation_results(gdf, output_path, max_grow_group_size)


def save_ids_map_csv(output_path: str, data: List[List]):
    header = ["SourceFilePath", "SourceID", "EntityID"]
    if not output_path:
        return
    for attempt in retrying_attempts():
        with attempt, vzg_open(output_path, "w") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for row in data:
                writer.writerow(row)


if __name__ == "__main__":
    initialize_filesystem()
    convert_geometry(parse_cmd_args())
