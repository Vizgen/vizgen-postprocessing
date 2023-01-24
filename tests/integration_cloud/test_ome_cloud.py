# flake8: noqa

from argparse import Namespace

import pytest

from tests.integration_cloud import CLOUD_TEMP_FILESYSTEMS
from tests.temp_dir import TempDir
from tests.test_convert_rgb_ome import test_rgb_ome, setup_rgb_ome
from tests.test_convert_to_ome import test_ome_metainfo, OmeTestScheme, setup_ome_arguments


@pytest.mark.parametrize('scheme',
                         [OmeTestScheme(f'ome_{str(temp_dir)}', ['mosaic_Cellbound1_z0.tif'], temp_dir)
                          for temp_dir in CLOUD_TEMP_FILESYSTEMS],
                         ids=str)
def test_ome_metainfo_cloud(scheme: OmeTestScheme, setup_ome_arguments: Namespace):
    test_ome_metainfo(scheme, setup_ome_arguments)


@pytest.mark.parametrize('test_dir', CLOUD_TEMP_FILESYSTEMS, ids=str)
def test_rgb_ome_cloud(test_dir: TempDir, setup_rgb_ome: Namespace):
    test_rgb_ome(test_dir, setup_rgb_ome)
