from argparse import Namespace

import numpy as np
import pytest
from vpt_core.io.vzgfs import get_rasterio_environment, rasterio_open
from vpt_core.utils.copy_utils import _copy_between_filesystems

from tests.vpt import IMAGES_ROOT
from tests.vpt.temp_dir import LocalTempDir, TempDir
from vpt.convert_to_ome.main_rgb import convert_to_ome_rgb
from vpt.convert_to_ome.tiffutils import read_image


@pytest.fixture()
def setup_rgb_ome(test_dir: TempDir) -> Namespace:
    path = test_dir.get_temp_path()
    sep = test_dir.get_sep()

    arguments = Namespace(
        input_image_red=sep.join([path, "mosaic_Cellbound1_z0.tif"]),
        input_image_green=sep.join([path, "mosaic_Cellbound2_z0.tif"]),
        input_image_blue=sep.join([path, "mosaic_DAPI_z0.tif"]),
        output_image=sep.join([path, "test_rgb_ome.tif"]),
        overwrite=False,
    )

    _copy_between_filesystems(str(IMAGES_ROOT / "mosaic_Cellbound1_z0.tif"), arguments.input_image_red)
    _copy_between_filesystems(str(IMAGES_ROOT / "mosaic_Cellbound2_z0.tif"), arguments.input_image_green)
    _copy_between_filesystems(str(IMAGES_ROOT / "mosaic_DAPI_z0.tif"), arguments.input_image_blue)

    yield arguments

    test_dir.clear_dir()


@pytest.mark.parametrize("test_dir", [LocalTempDir()], ids=str)
def test_rgb_ome(test_dir: TempDir, setup_rgb_ome: Namespace):
    convert_to_ome_rgb(setup_rgb_ome)
    with get_rasterio_environment(setup_rgb_ome.output_image):
        with rasterio_open(setup_rgb_ome.input_image_red) as file_r, rasterio_open(
            setup_rgb_ome.input_image_green
        ) as file_g, rasterio_open(setup_rgb_ome.input_image_blue) as file_b:
            r_image, g_image, b_image = file_r.read(1), file_b.read(1), file_g.read(1)
            with read_image(setup_rgb_ome.output_image, n=-1) as result:
                array_result = np.array(result)
                assert (array_result[: len(r_image)] == r_image).all()
                assert (array_result[len(r_image) : 2 * len(g_image)] == b_image).all()
                assert (array_result[2 * len(b_image) :] == g_image).all()


@pytest.mark.parametrize("test_dir", [LocalTempDir()], ids=str)
def test_rgb_ome_dirs(test_dir: TempDir, setup_rgb_ome: Namespace):
    args = setup_rgb_ome
    args.output_image = args.output_image.replace("test_rgb_ome.tif", "")
    try:
        convert_to_ome_rgb(setup_rgb_ome)
    except ValueError:
        return
    assert False
