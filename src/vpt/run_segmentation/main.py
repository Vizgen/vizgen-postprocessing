import argparse
import json

from vpt_core import log
from vpt_core.io.vzgfs import io_with_retries

from vpt.app.context import parallel_run
from vpt.app.task import pipeline_to_tasks
from vpt.compile_tile_segmentation import run as compile_tile_segmentation
from vpt.prepare_segmentation import run as run_prepare_segmentation
from vpt.prepare_segmentation.constants import OUTPUT_FILE_NAME
from vpt.run_segmentation.cmd_args import RunSegmentationArgs, validate_args


def run_segmentation(args: argparse.Namespace):
    def to_prepare_segmentation_args(rsargs: RunSegmentationArgs) -> argparse.Namespace:
        prep_args = dict(vars(rsargs))
        prep_args.pop("max_row_group_size")
        return argparse.Namespace(**prep_args)

    rs_args = RunSegmentationArgs(**vars(args))
    validate_args(rs_args)
    log.info("run_segmentation started")
    run_prepare_segmentation(to_prepare_segmentation_args(rs_args))

    spec_path = "/".join([rs_args.output_path, OUTPUT_FILE_NAME])

    spec_json = io_with_retries(spec_path, "r", json.load)

    num_tiles = spec_json["window_grid"]["num_tiles"]

    rot_args = [
        argparse.Namespace(input_segmentation_parameters=spec_path, tile_index=i, overwrite=rs_args.overwrite)
        for i in range(num_tiles)
    ]

    parallel_run(pipeline_to_tasks("run-segmentation-on-tile", rot_args))

    compile_args = argparse.Namespace(
        input_segmentation_parameters=spec_path,
        max_row_group_size=rs_args.max_row_group_size,
        overwrite=rs_args.overwrite,
    )

    compile_tile_segmentation(compile_args)

    log.info("run_segmentation finished")
