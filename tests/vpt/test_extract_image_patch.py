import os
from argparse import Namespace
import numpy as np
import pytest

from vpt_core.io.regex_tools import ImagePath, RegexInfo
from tests.vpt import IMAGES_ROOT, IMAGES_ROOT_MOCK, OUTPUT_FOLDER, TEST_DATA_ROOT
from vpt.extract_image_patch.main import extract_image_patch
from vpt.utils.input_utils import read_micron_to_mosaic_transform
from vpt.utils.process_patch import ExtractImageArgs, process_patch


EXTRACT_IMAGE_CASES = [
    Namespace(
        input_images=str(IMAGES_ROOT),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
        center_x=20,
        center_y=0,
        green_stain_name="Cellbound2",
        output_patch=str(OUTPUT_FOLDER / "test.png"),
        size_x=10.8,
        size_y=10.8,
        input_z_index=3,
        red_stain_name="Cellbound1",
        blue_stain_name="DAPI",
        normalization="CLAHE",
        overwrite=False,
    ),
    Namespace(
        input_images=str(IMAGES_ROOT),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
        center_x=20,
        center_y=0,
        green_stain_name="Cellbound2",
        output_patch=str(OUTPUT_FOLDER / "test.png"),
        size_x=10.8,
        size_y=10.8,
        input_z_index=0,
        red_stain_name=None,
        blue_stain_name="DAPI",
        normalization="none",
        overwrite=True,
    ),
    Namespace(
        input_images=str(IMAGES_ROOT),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
        center_x=20,
        center_y=0,
        green_stain_name="Cellbound2",
        output_patch=str(OUTPUT_FOLDER / "test.png"),
        size_x=10.8,
        size_y=10.8,
        input_z_index=1,
        red_stain_name=None,
        blue_stain_name=None,
        normalization="range",
        overwrite=True,
    ),
    Namespace(
        input_images=str(IMAGES_ROOT),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
        center_x=20,
        center_y=0,
        green_stain_name="Cellbound2",
        output_patch=str(OUTPUT_FOLDER / "test.png"),
        size_x=10.8,
        size_y=12.2,
        input_z_index=1,
        red_stain_name=None,
        blue_stain_name=None,
        normalization="range",
        overwrite=True,
    ),
]


@pytest.mark.parametrize("fakesNamespaceArgs", EXTRACT_IMAGE_CASES)
def test_extract_image_patch(fakesNamespaceArgs: Namespace):
    extract_image_patch(fakesNamespaceArgs)
    assert os.path.exists(fakesNamespaceArgs.output_patch)

    if os.path.exists(fakesNamespaceArgs.output_patch):
        os.remove(fakesNamespaceArgs.output_patch)


EXTRACT_IMAGE_CASES_FAIL = [
    Namespace(
        input_images=str(IMAGES_ROOT),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
        center_x=0,
        center_y=0,
        green_stain_name="Cellbound2",
        output_patch=str(OUTPUT_FOLDER / "test.png"),
        size_x=10.8,
        size_y=10.8,
        input_z_index=3,
        red_stain_name="Cellbound1",
        blue_stain_name="DAPI",
        normalization="CLAHE",
        overwrite=False,
    ),
    Namespace(
        input_images=str(IMAGES_ROOT),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
        center_x=20,
        center_y=0,
        green_stain_name="Cellbound2",
        output_patch=str(OUTPUT_FOLDER / "test.png"),
        size_x=10.8,
        size_y=10.8,
        input_z_index=-1,
        red_stain_name=None,
        blue_stain_name="DAPI",
        normalization="none",
        overwrite=True,
    ),
    Namespace(
        input_images=str(IMAGES_ROOT),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
        center_x=20,
        center_y=0,
        green_stain_name="Cellbound2",
        output_patch=str(OUTPUT_FOLDER / "test.png"),
        size_x=-1,
        size_y=10.8,
        input_z_index=1,
        red_stain_name=None,
        blue_stain_name=None,
        normalization="range",
        overwrite=True,
    ),
    Namespace(
        input_images=str(IMAGES_ROOT),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
        center_x=20,
        center_y=0,
        green_stain_name="Cellbound2",
        output_patch=str(OUTPUT_FOLDER / "test.png"),
        size_x=10.8,
        size_y=10.8,
        input_z_index=1,
        red_stain_name=None,
        blue_stain_name=None,
        normalization="gaussian",
        overwrite=True,
    ),
]


@pytest.mark.parametrize("fakesNamespaceArgs", EXTRACT_IMAGE_CASES_FAIL)
def test_extract_image_patch_fail(fakesNamespaceArgs: Namespace):
    with pytest.raises(ValueError):
        extract_image_patch(fakesNamespaceArgs)

    if os.path.exists(fakesNamespaceArgs.output_patch):
        os.remove(fakesNamespaceArgs.output_patch)


def test_process_patch():
    image_path = ImagePath(channel="MOCK", z_layer=0, full_path=str(IMAGES_ROOT_MOCK / "mosaic_MOCK_z0.tif"))

    regex_info = RegexInfo(image_width=5000, image_height=200, images={image_path})

    m2m_transform = read_micron_to_mosaic_transform(
        str(TEST_DATA_ROOT / IMAGES_ROOT_MOCK / "micron_to_mosaic_pixel_transform.csv")
    )

    extract_image_args = ExtractImageArgs(
        images=regex_info,
        m2m_transform=m2m_transform,
        center_x=200,
        center_y=5,
        output_patch="",
        size_x=5,
        size_y=5,
        input_z_index=0,
        red_stain_name="",
        green_stain_name="MOCK",
        blue_stain_name="",
        normalization="clahe",
        overwrite=False,
    )

    patch = process_patch(extract_args=extract_image_args)
    assert isinstance(patch, np.ndarray) and patch.size > 0
