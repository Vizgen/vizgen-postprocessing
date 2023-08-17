from typing import List, Tuple

import numpy as np
from vpt_core import log
from vpt_core.io.image import get_prepared_images, get_segmentation_images
from vpt_core.segmentation.fuse import fuse_task_polygons
from vpt_core.segmentation.polygon_utils import get_upscale_matrix
from vpt_core.segmentation.seg_result import SegmentationResult

from vpt.entity.relationships import create_entity_relationships
from vpt.run_segmentation_on_tile.cmd_args import RunOnTileCmdArgs, parse_cmd_args, validate_cmd_args
from vpt.utils.seg_spec_utils import SegSpec, read_seg_spec, validate_seg_spec
from vpt.run_segmentation_on_tile.output_utils import save_to_parquet
from vpt.segmentation.segmentations_factory import get_seg_implementation


def get_tile_segmentation(seg_spec: SegSpec, window_info: Tuple[int, int, int, int]):
    tasks_result = []
    fusion_info = seg_spec.segmentation_task_fusion

    for task in seg_spec.segmentation_tasks:
        # Perform segmentation, returns a SegmentationResult set of polygons
        images = get_segmentation_images(seg_spec.images, window_info)
        images, scale = get_prepared_images(task, images)
        runner = get_seg_implementation(task.segmentation_family).run_segmentation
        seg_result = runner(
            segmentation_properties=task.segmentation_properties,
            segmentation_parameters=task.segmentation_parameters,
            polygon_parameters=task.polygon_parameters,
            result=task.entity_types_detected,
            images=images,
        )

        # Remove images from memory once the geometries are produced
        del images

        res_num = len(task.entity_types_detected)
        if not hasattr(seg_result, "__iter__"):
            if res_num > 1:
                raise ValueError(
                    f"Segmentation result for task {task.task_id} should be iterable and have " f"{res_num} elements"
                )
            seg_result = [seg_result]

        for i, entity_result in enumerate(seg_result):
            entity_type = task.entity_types_detected[i]
            tasks_result.append(
                postprocess_seg_result(
                    entity_result,
                    task,
                    entity_type,
                    scale,
                    window_info,
                    fusion_info[entity_type],
                    seg_spec.experiment_properties.all_z_indexes,
                )
            )

    return tasks_result


def postprocess_seg_result(
    seg_result, task, entity_type, scale, window_info, fusion_info, z_indexes
) -> SegmentationResult:
    log.info(f"raw segmentation result contains {len(seg_result.df.index)} rows")
    if task.segmentation_properties["model_dimensions"] == "2D":
        log.info("fuze across z")
        seg_result.update_column(SegmentationResult.z_index_field, lambda i: task.z_layers[i])
        seg_result.fuse_across_z()
        seg_result.replicate_across_z(z_indexes)

    seg_result.transform_geoms(get_upscale_matrix(scale[0], scale[1]))
    log.info("remove edge polys")
    seg_result.remove_edge_polys((window_info[2],) * 2)
    seg_result.set_entity_type(entity_type)

    if seg_result.df[seg_result.cell_id_field].gt(seg_result.MAX_ENTITY_ID).any():
        raise OverflowError(f"Tile segmentation could not have more than {seg_result.MAX_ENTITY_ID} entities")

    return SegmentationResult.reindex_by_task([seg_result], [task.task_id])[0]


def segmentation_on_tile(seg_spec: SegSpec, tile_index: int) -> List[SegmentationResult]:
    window_info = seg_spec.image_windows[tile_index]
    log.info(f"Tile {tile_index} {window_info}")

    tasks_result = get_tile_segmentation(seg_spec, window_info)

    tasks_result = fuse_task_polygons(tasks_result, seg_spec.segmentation_task_fusion)
    tasks_result = create_entity_relationships(
        tasks_result,
        seg_spec.entity_type_relationships,
        {
            entity: seg_spec.segmentation_task_fusion[entity].fused_polygon_postprocessing_parameters
            for entity in seg_spec.segmentation_task_fusion.keys()
        },
    )
    mosaic_to_micron_matrix = np.linalg.inv(seg_spec.micron_to_mosaic_tform)
    for i in range(len(tasks_result)):
        tasks_result[i].translate_geoms(window_info[0], window_info[1])
        tasks_result[i].transform_geoms(mosaic_to_micron_matrix)
    return tasks_result


def run_segmentation_on_tile(parsed_args):
    args = RunOnTileCmdArgs(**vars(parsed_args))
    validate_cmd_args(args)
    log.info(f"Run segmentation on tile {args.tile_index} started")

    seg_spec = read_seg_spec(args.input_segmentation_parameters, args.overwrite)
    validate_seg_spec(seg_spec, args.tile_index, args.overwrite)

    result = segmentation_on_tile(seg_spec, args.tile_index)

    save_to_parquet(
        result,
        args.tile_index,
        seg_spec.timestamp,
        seg_spec.experiment_properties.z_positions_um,
        seg_spec.output_paths,
    )
    log.info(f"Run segmentation on tile {args.tile_index} finished")


def main():
    args = parse_cmd_args()
    run_segmentation_on_tile(args)
