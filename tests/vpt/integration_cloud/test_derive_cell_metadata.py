import pytest
from vpt_core.io.vzgfs import initialize_filesystem

from tests.vpt.integration_cloud import CLOUD_TEMP_FILESYSTEMS
from tests.vpt.temp_dir import TempDir
from tests.vpt.test_gen_cell_metadata import test_func_derive_cell_metadata


@pytest.mark.parametrize("temp_dir", CLOUD_TEMP_FILESYSTEMS, ids=str)
def test_func_derive_cell_metadata_cloud(temp_dir: TempDir):
    initialize_filesystem()
    test_func_derive_cell_metadata(temp_dir)
