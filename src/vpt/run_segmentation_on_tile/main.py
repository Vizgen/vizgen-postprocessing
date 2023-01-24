from typing import List

import numpy as np
from vpt.run_segmentation_on_tile.cmd_args import parse_cmd_args, RunOnTileCmdArgs, validate_cmd_args
from vpt.run_segmentation_on_tile.image import get_prepared_images, get_segmentation_images
from vpt.run_segmentation_on_tile.input_utils import read_seg_spec, validate_seg_spec, SegSpec
from vpt.run_segmentation_on_tile.output_utils import save_to_parquet
from vpt.segmentation.utils.fuse import fuse_task_polygons
from vpt.segmentation.factory import run_segmentation
from vpt.segmentation.utils.polygon_utils import get_upscale_matrix
from vpt.segmentation.utils.seg_result import SegmentationResult
import vpt.log as log


def add_task_to_entity_id(old_id, task_number) -> int:
    entity_str_len = len(str(SegmentationResult.MAX_ENTITY_ID))
    task_str_len = len(str(SegmentationResult.MAX_TASK_ID))

    old_id_str = str(old_id).zfill(entity_str_len)
    task_str = str(task_number + 1).zfill(task_str_len)

    if len(old_id_str) > entity_str_len or len(task_str) > task_str_len:
        raise OverflowError('EntityID is out of the int64 type range')
    return np.int64(''.join([task_str, old_id_str]))


def reindex_by_task(tasks_results: List[SegmentationResult], tasks_numbers: List[int]):
    for task_i in range(len(tasks_results)):
        tasks_results[task_i].update_column(SegmentationResult.cell_id_field, add_task_to_entity_id,
                                            task_number=tasks_numbers[task_i])
    return tasks_results


def get_tile_segmentation(
    seg_spec: SegSpec,
    window_info: List[int]
):
    tasks_result, tasks_numbers = [], []
    fusion_info = seg_spec.segmentation_task_fusion
    seg_properties = seg_spec.experiment_properties

    for task in seg_spec.segmentation_tasks:
        # Perform segmentation, returns a SegmentationResult set of polygons
        images = get_segmentation_images(seg_spec.images, window_info)
        images, scale = get_prepared_images(task, images)
        seg_result = run_segmentation(images, task)

        # Remove images from memory once the geometries are produced
        del images

        # Process raw geometry into final segmentation output
        log.info(f"raw segmentation result contains {len(seg_result.df.index)} rows")
        if task.segmentation_properties['model_dimensions'] == '2D':
            log.info("fuze across z")
            seg_result.update_column(SegmentationResult.z_index_field, lambda i: task.z_layers[i])
            seg_result.fuse_across_z(fusion_info.fused_polygon_postprocessing_parameters)
            seg_result.replicate_across_z(seg_properties.all_z_indexes)

        seg_result.transform_geoms(get_upscale_matrix(scale[0], scale[1]))
        log.info("remove edge polys")
        seg_result.remove_edge_polys((window_info[2],) * 2)
        seg_result.set_entity_type(task.entity_types_detected)

        if seg_result.df[seg_result.cell_id_field].gt(seg_result.MAX_ENTITY_ID).any():
            raise OverflowError(f'Tile segmentation could not have more than {seg_result.MAX_ENTITY_ID} entities')

        tasks_result.append(seg_result)
        tasks_numbers.append(task.task_id)

    tasks_result = reindex_by_task(tasks_result, tasks_numbers)

    return tasks_result


def segmentation_on_tile(seg_spec: SegSpec, tile_index: int) -> List[SegmentationResult]:
    window_info = seg_spec.image_windows[tile_index]
    log.info(f"Tile {tile_index} {window_info}")

    tasks_result = get_tile_segmentation(seg_spec, window_info)

    fused_result = fuse_task_polygons(tasks_result, seg_spec.segmentation_task_fusion)
    mosaic_to_micron_matrix = np.linalg.inv(seg_spec.micron_to_mosaic_tform)
    for i in range(len(fused_result)):
        fused_result[i].translate_geoms(window_info[0], window_info[1])
        fused_result[i].transform_geoms(mosaic_to_micron_matrix)
    return fused_result


def run_segmentation_on_tile(parsed_args):
    args = RunOnTileCmdArgs(**vars(parsed_args))
    validate_cmd_args(args)
    log.info(f"Run segmentation on tile {args.tile_index} started")

    seg_spec = read_seg_spec(args.input_segmentation_parameters, args.overwrite)
    validate_seg_spec(seg_spec, args.tile_index, args.overwrite)

    result = segmentation_on_tile(seg_spec, args.tile_index)

    save_to_parquet(result, args.tile_index, seg_spec.timestamp, seg_spec.experiment_properties.z_positions_um,
                    seg_spec.output_paths)
    log.info(f"Run segmentation on tile {args.tile_index} finished")


def main():
    args = parse_cmd_args()
    run_segmentation_on_tile(args)
