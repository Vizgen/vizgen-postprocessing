from argparse import Namespace
from typing import List

import pytest

from tests import IMAGES_ROOT
from tests.temp_dir import TempDir, LocalTempDir
from tests.utils import _copy_between_filesystems
from vpt.convert_to_ome.main import convert_to_ome
from vpt.convert_to_ome.tiffutils import read_image
from vpt.filesystem.vzgfs import get_rasterio_environment, rasterio_open


class OmeTestScheme:
    def __init__(self, name: str, images_paths: List[str], temp_dir: TempDir):
        self.name = name
        self.images_paths = images_paths
        self.temp_dir = temp_dir
        self.images_dir_name = 'input_images'
        self.output_dir_name = 'output_images'

    def __str__(self):
        return self.name


@pytest.fixture()
def setup_ome_arguments(scheme: OmeTestScheme) -> Namespace:
    path = scheme.temp_dir.get_temp_path()
    sep = scheme.temp_dir.get_sep()
    arguments = Namespace(
        input_image=sep.join([path, scheme.images_dir_name]),
        output_image=sep.join([path, scheme.output_dir_name]),
        overwrite=False
    )

    scheme.temp_dir.create_dir(scheme.output_dir_name)
    scheme.temp_dir.create_dir(scheme.images_dir_name)

    if len(scheme.images_paths) > 1:
        for im_path in scheme.images_paths:
            _copy_between_filesystems(str(IMAGES_ROOT / im_path), sep.join([arguments.input_image, im_path]))
    else:
        arguments.output_image = sep.join([arguments.output_image, scheme.images_paths[0].replace('.tif', '.ome.tif')])
        arguments.input_image = sep.join([arguments.input_image, scheme.images_paths[0]])
        _copy_between_filesystems(str(IMAGES_ROOT / scheme.images_paths[0]), arguments.input_image)

    yield arguments

    scheme.temp_dir.clear_dir()


@pytest.mark.parametrize('scheme', [
    OmeTestScheme('ome', ['mosaic_Cellbound1_z0.tif'], LocalTempDir()),
    OmeTestScheme('ome_dir', ['mosaic_Cellbound1_z0.tif', 'mosaic_Cellbound1_z0.tif'], LocalTempDir()),
    ], ids=str)
def test_ome_metainfo(scheme: OmeTestScheme, setup_ome_arguments: Namespace):
    convert_to_ome(setup_ome_arguments)
    sep = scheme.temp_dir.get_sep()
    tmp_path = scheme.temp_dir.get_temp_path()
    for image_path in scheme.images_paths:
        input_path = sep.join([tmp_path, scheme.images_dir_name, image_path])
        output_path = sep.join([tmp_path, scheme.output_dir_name, image_path.replace('.tif', '.ome.tif')])
        with get_rasterio_environment(output_path):
            with rasterio_open(output_path) as file:
                res_image = file.read(1)
                with rasterio_open(input_path) as file:
                    gt_image = file.read(1)
                    assert (res_image == gt_image).all()

        with read_image(output_path) as res_pyvips:
            ome_metainfo = res_pyvips.get('image-description')
            assert ome_metainfo.startswith("""<?xml version="1.0" encoding="UTF-8"?>""")
            assert ome_metainfo.find("SizeC=\"1\"") >= 0
            assert ome_metainfo.find(f"SizeX=\"{len(gt_image)}\"") >= 0
