import dataclasses
from typing import Callable, Dict, List, Tuple

import numpy as np
from vpt_core.image.filter import normalization_clahe, normalize
from vpt_core.io.image import read_tile
from vpt_core.io.regex_tools import RegexInfo, parse_images_str

from vpt.extract_image_patch import clahe_params
from vpt.extract_image_patch.cmd_args import ExtractImagePatchArgs
from vpt.utils.input_utils import read_micron_to_mosaic_transform


@dataclasses.dataclass
class ExtractImageArgs:
    images: RegexInfo
    m2m_transform: List[float]
    center_x: float
    center_y: float
    output_patch: str
    size_x: float
    size_y: float
    input_z_index: int
    red_stain_name: str
    green_stain_name: str
    blue_stain_name: str
    normalization: str
    overwrite: bool


def load_paths_args(extract_args: ExtractImagePatchArgs) -> ExtractImageArgs:
    extract_params = vars(extract_args).copy()
    extract_params.pop("input_images")
    extract_params.pop("input_micron_to_mosaic")

    m2m_transform = read_micron_to_mosaic_transform(extract_args.input_micron_to_mosaic)

    extract_params["images"] = parse_images_str(extract_args.input_images)
    extract_params["m2m_transform"] = m2m_transform
    return ExtractImageArgs(**extract_params)


def transform_point(viz_coords: List, m2m_pixel_transform: List, offset: bool) -> Tuple:
    m2m_transform = np.asarray(m2m_pixel_transform, dtype=float)
    point = np.array([[viz_coords[0], viz_coords[1]]])
    scaled = np.matmul(point, m2m_transform[0:2, 0:2])
    if offset:
        translated = np.array([scaled[0, 0] + m2m_transform[0, 2], scaled[0, 1] + m2m_transform[1, 2]])
    else:
        translated = np.array([scaled[0, 0], scaled[0, 1]])
    x, y = translated
    return (int(x), int(y))


def transform_coords(extract_args: ExtractImageArgs) -> List:
    coords_start = [
        extract_args.center_x - (extract_args.size_x / 2),
        extract_args.center_y - (extract_args.size_y / 2),
    ]
    coords_size = [extract_args.size_x, extract_args.size_y]

    start_coords_mosaic = transform_point(coords_start, extract_args.m2m_transform, offset=True)
    size_coords_mosaic = transform_point(coords_size, extract_args.m2m_transform, offset=False)
    window = [start_coords_mosaic[0], start_coords_mosaic[1], size_coords_mosaic[0], size_coords_mosaic[1]]
    return window


def convert_dtype(image: np.ndarray) -> np.ndarray:
    converted_image = np.right_shift(image, 8).astype(np.uint8)
    return converted_image


def create_paths(extract_args: ExtractImageArgs) -> Tuple:
    chan_to_color = {
        extract_args.red_stain_name: "red",
        extract_args.green_stain_name: "green",
        extract_args.blue_stain_name: "blue",
    }
    chan_to_color = {key.lower() if isinstance(key, str) else key: value for key, value in chan_to_color.items()}

    color_to_path = {}
    for image_path in extract_args.images.images:
        if image_path.channel.lower() in chan_to_color.keys() and image_path.z_layer == extract_args.input_z_index:
            color_to_path[chan_to_color[image_path.channel.lower()]] = image_path.full_path

    return extract_args.images.image_width, extract_args.images.image_height, color_to_path


def validate_patch(patch_window: List, width: int, height: int):
    if patch_window[0] < 0 or patch_window[1] < 0 or patch_window[0] > width or patch_window[1] > height:
        raise ValueError(
            f"Either the patch start width coordinate ({patch_window[0]}), or the patch height coordinate ({patch_window[1]}), is outside the image range [(0, {width}), (0, {height})]. Move the patch center."
        )

    end_coords = [patch_window[0] + patch_window[2], patch_window[1] + patch_window[3]]
    if end_coords[0] > width or end_coords[1] > height:
        raise ValueError(
            f"Either the patch end width coordinate ({end_coords[0]}) is larger than the mosaic width ({width}), or the patch end height coordinate ({end_coords[1]}) is larger than the mosaic height ({height})"
        )


def make_png(output_patch: str) -> str:
    if not output_patch.endswith(".png") and not output_patch.endswith(".PNG"):
        return output_patch + ".png"
    else:
        return output_patch


def make_html(output_report: str) -> str:
    if not output_report.endswith(".html") and not output_report.endswith(".HTML"):
        return output_report + ".html"
    else:
        return output_report


def process_patch(extract_args: ExtractImageArgs, image_reader=read_tile) -> np.ndarray:
    patch_window = transform_coords(extract_args)
    # The size of the rasterio window has a (y, x) form, so swap the values to create numpy arrays
    patch_shape = (patch_window[-1], patch_window[-2])
    patch_data = {
        "red": np.zeros(shape=patch_shape, dtype=np.uint16),
        "green": np.zeros(shape=patch_shape, dtype=np.uint16),
        "blue": np.zeros(shape=patch_shape, dtype=np.uint16),
    }

    width, height, color_to_path = create_paths(extract_args)
    validate_patch(patch_window, width, height)

    for color, path in color_to_path.items():
        patch_data[color] = image_reader(patch_window, path)

    factory_map: Dict[str, Callable] = {
        "none": convert_dtype,
        "range": normalize,
        "clahe": lambda x: normalization_clahe(x, clahe_params),
    }

    filter = factory_map[extract_args.normalization.lower()]
    patch = np.stack(
        (filter(patch_data.get("red")), filter(patch_data.get("green")), filter(patch_data.get("blue"))), axis=-1
    )
    return patch
