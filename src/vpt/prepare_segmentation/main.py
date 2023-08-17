from datetime import datetime
from typing import Dict

import numpy as np

from vpt.utils.metadata import get_installed_versions
from vpt_core import log
from vpt_core.io.regex_tools import parse_images_str
from vpt_core.segmentation.seg_result import SegmentationResult

from vpt.prepare_segmentation.cmd_args import PrepareSegmentationArgs, parse_args, validate_prepare_segmentation_args
from vpt.prepare_segmentation.input_tools import parse_algorithm_json, read_json
from vpt.prepare_segmentation.output_tools import save_to_json
from vpt.prepare_segmentation.tiles import make_tiles
from vpt.prepare_segmentation.validate import validate_alg_info, validate_regex_and_alg_match
from vpt.utils.input_utils import read_micron_to_mosaic_transform


def run_prepare_segmentation(args):
    if args.tile_overlap is None:
        args.tile_overlap = int(0.1 * args.tile_size)
    args = PrepareSegmentationArgs(**vars(args))
    log.info("prepare segmentation started")
    validate_prepare_segmentation_args(args)

    algorithm_json = read_json(args.segmentation_algorithm)

    m2m_transform = read_micron_to_mosaic_transform(args.input_micron_to_mosaic)

    seg_spec = get_segmentation_spec(
        algorithm_json,
        args.input_images,
        m2m_transform,
        args.tile_size,
        args.tile_overlap,
        args.segmentation_algorithm,
        args.input_micron_to_mosaic,
        args.output_path,
        args.overwrite,
    )

    save_to_json(seg_spec, args.output_path)
    log.info("prepare segmentation finished")


def get_segmentation_spec(
    algorithm_json: Dict,
    input_images_regex: str,
    micron_to_mosaic_matrix: np.ndarray,
    tile_size: int,
    tile_overlap: int,
    algorithm_path: str,
    micron_to_mosaic_path: str,
    output_path: str,
    overwrite: bool = False,
):
    alg_info = parse_algorithm_json(algorithm_json)
    alg_info = validate_alg_info(alg_info, output_path, overwrite)

    regex_info = parse_images_str(input_images_regex)
    validate_regex_and_alg_match(regex_info, alg_info)

    timestamp = datetime.now().timestamp()

    tile_info = make_tiles(regex_info.image_width, regex_info.image_height, tile_size, tile_overlap)
    if len(tile_info) > SegmentationResult.MAX_TILE_ID:
        raise OverflowError(f"Number of tiles in experiment could not be greater than {SegmentationResult.MAX_TILE_ID}")
    return {
        "timestamp": timestamp,
        "input_args": {
            "segmentation_algorithm": algorithm_path,
            "input_path": input_images_regex,
            "input_micron_to_mosaic_path": micron_to_mosaic_path,
            "output_path": output_path,
            "tile_size": tile_size,
            "tile_overlap": tile_overlap,
        },
        "installed_versions": get_installed_versions(),
        "input_data": {
            "micron_to_mosaic_tform": micron_to_mosaic_matrix,
            "z_layers": list(alg_info.z_layers),
            "channels": list(alg_info.stains),
            "images": [
                {"channel": image.channel, "z_layer": image.z_layer, "full_path": image.full_path}
                for image in regex_info.images
                if image.channel in alg_info.stains and image.z_layer in alg_info.z_layers
            ],
        },
        "window_grid": {
            "mosaic_size": [regex_info.image_width, regex_info.image_height],
            "tile_size": [tile_size, tile_size],
            "tile_overlap": tile_overlap,
            "num_tiles": len(tile_info),
            "windows": [[tile.top_left_x, tile.top_left_y, tile.size, tile.size] for tile in tile_info],
        },
        "segmentation_algorithm": alg_info.raw,
    }


if __name__ == "__main__":
    run_prepare_segmentation(parse_args())
