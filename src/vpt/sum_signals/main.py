import argparse
from collections import defaultdict
from typing import Iterable, Tuple

import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from scipy import ndimage
from shapely.affinity import affine_transform, translate
from shapely.geometry.base import BaseGeometry
from vpt_core import log
from vpt_core.io.regex_tools import parse_images_str
from vpt_core.io.vzgfs import (
    filesystem_path_split,
    get_rasterio_environment,
    initialize_filesystem,
    rasterio_open,
    io_with_retries,
)
from vpt_core.log import show_progress
from vpt_core.segmentation.seg_result import SegmentationResult

from vpt.app.context import current_context, parallel_run
from vpt.app.task import Task
from vpt.sum_signals.cmd_args import SumSignalsArgs, parse_args, validate_args
from vpt.sum_signals.validate import validate_z_layers_number
from vpt.utils.input_utils import read_geodataframe, read_micron_to_mosaic_transform, read_parquet_by_groups


def get_cell_brightness_in_image(image_path: str, entities: Iterable[Tuple[int, BaseGeometry]]) -> tuple:
    cell_raw_brightness = []
    cell_filtered_brightness = []
    indexes = []

    with get_rasterio_environment(image_path):
        with rasterio_open(image_path) as file:
            for cell_id, cell in entities:
                if cell is None or cell.is_empty:
                    continue

                # Define an image area to read
                rasterio_window = [
                    cell.bounds[0],
                    cell.bounds[1],
                    cell.bounds[2] - cell.bounds[0] + 1,
                    cell.bounds[3] - cell.bounds[1] + 1,
                ]

                # Read the image area and convert to 2D numpy array
                rasterio_window = [int(x) for x in rasterio_window]
                image_data = file.read(1, window=rasterio.windows.Window(*rasterio_window))

                high_pass_input = image_data
                cell_fft = np.fft.fft2(high_pass_input)
                filtered_fft = ndimage.fourier_uniform(cell_fft, size=10)
                inverse_filtered_fft = np.fft.ifft2(filtered_fft)
                high_pass_image = high_pass_input - inverse_filtered_fft.real
                high_pass_image = np.maximum(high_pass_image, 0)

                try:
                    # Create a polygon at the origin to use to mask an image
                    selector_poly = translate(cell, xoff=-cell.bounds[0], yoff=-cell.bounds[1])

                    # Create the mask
                    bounding_box = [int(x) for x in selector_poly.bounds]
                    if (
                        min(bounding_box[:2]) < 0
                        or bounding_box[2] >= image_data.shape[1]
                        or bounding_box[3] >= image_data.shape[0]
                    ):
                        raise ValueError(f"Cell is beyond image boundaries: {cell}")

                    mask_shape = (bounding_box[3] + 1, bounding_box[2] + 1)
                    cell_mask = rasterize([selector_poly], out_shape=mask_shape, all_touched=True)
                    temp_raw = np.sum(image_data * cell_mask)
                    temp_filt = np.sum(high_pass_image * cell_mask)
                except ValueError:
                    log.warning(f"Could not apply cell mask for Entity {cell_id} in image {image_path}")
                    temp_raw = np.sum(image_data)
                    temp_filt = np.sum(high_pass_image)

                cell_raw_brightness.append(temp_raw)
                cell_filtered_brightness.append(temp_filt)
                indexes.append(cell_id)

    return (pd.Series(cell_raw_brightness, index=indexes), pd.Series(cell_filtered_brightness, index=indexes))


def calculate(args):
    img, fn_boundaries, transform = args.img, args.boundaries, args.transform
    log.info(f"sum_signals.calculate for {img.full_path} started")

    def iterator() -> Iterable[Tuple[int, BaseGeometry]]:
        for parquet_data in read_parquet_by_groups(fn_boundaries):
            for _, row in parquet_data.loc[parquet_data[SegmentationResult.z_index_field] == img.z_layer].iterrows():
                entity_id = row[SegmentationResult.cell_id_field]
                geom = row[SegmentationResult.geometry_field]
                yield entity_id, affine_transform(geom, transform)

    res = get_cell_brightness_in_image(img.full_path, iterator())
    return img.channel, res


def validate_and_prepare_ids(images, fn_boundary):
    boundaries = read_geodataframe(fn_boundary)
    validate_z_layers_number(images, boundaries)
    return boundaries["EntityID"].unique()


def get_cell_brightnesses(images, fn_boundary, transform):
    ids = validate_and_prepare_ids(images, fn_boundary)

    def default_value():
        return pd.Series(np.zeros(len(ids)), index=ids)

    results_raw, results_high_pass = defaultdict(default_value), defaultdict(default_value)
    log.info("output structures prepared")
    results = parallel_run(
        [Task(calculate, argparse.Namespace(img=img, boundaries=fn_boundary, transform=transform)) for img in images]
    )

    def combine_results(jobs, progress=False):
        if progress:
            jobs = show_progress(jobs, total=len(results))
        log.info("all jobs finished")
        for channel, (intensities_raw, intensities_high_pass) in jobs:
            results_raw[channel][intensities_raw.index] += intensities_raw
            results_high_pass[channel][intensities_high_pass.index] += intensities_high_pass

    ctx = current_context()
    combine_results(results, progress=ctx is None or ctx.get_workers_count() == 1)
    log.info("results combined")

    assert set(results_raw.keys()) == set(results_high_pass.keys())

    sum_signals_data = {}
    for stain in results_raw.keys():
        sum_signals_data[f"{stain}_raw"] = results_raw[stain]
        sum_signals_data[f"{stain}_high_pass"] = results_high_pass[stain]

    df = pd.DataFrame(sum_signals_data)
    df.sort_index(inplace=True)

    return df


def save_df(df, path: str):
    fs, fs_path = filesystem_path_split(path)
    try:
        parent, _ = fs_path.rsplit(fs.sep, maxsplit=1)  # raises ValueError if the path only contains a filename
        fs.mkdirs(parent, exist_ok=True)
    except ValueError:
        pass

    io_with_retries(path, "w", df.to_csv)


def sum_signals(args: argparse.Namespace):
    sum_signals_args = SumSignalsArgs(**vars(args))
    validate_args(sum_signals_args)
    log.info("Sum signals started")
    regex_info = parse_images_str(sum_signals_args.input_images)

    m2m = np.array(read_micron_to_mosaic_transform(sum_signals_args.input_micron_to_mosaic))
    tform_flat = [*m2m[:2, :2].flatten(), *m2m[:2, 2].flatten()]

    df = get_cell_brightnesses(regex_info.images, sum_signals_args.input_boundaries, tform_flat)

    save_df(df, sum_signals_args.output_csv)
    log.info("Sum signals finished")


if __name__ == "__main__":
    initialize_filesystem()
    sum_signals(parse_args())
