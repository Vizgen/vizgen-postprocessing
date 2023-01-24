import pytest

from tests.integration_cloud import CLOUD_TEMP_FILESYSTEMS
from tests.temp_dir import TempDir
from tests.test_gen_cell_metadata import test_func_derive_cell_metadata
from vpt.filesystem import initialize_filesystem


@pytest.mark.parametrize('temp_dir', CLOUD_TEMP_FILESYSTEMS, ids=str)
def test_func_derive_cell_metadata_cloud(temp_dir: TempDir):
    initialize_filesystem()
    test_func_derive_cell_metadata(temp_dir)
