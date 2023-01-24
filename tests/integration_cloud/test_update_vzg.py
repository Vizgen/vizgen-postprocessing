import pytest

from tests.integration_cloud import CLOUD_TEMP_FILESYSTEMS
from tests.temp_dir import TempDir
from tests.test_update_vzg import test_func_local_update_vzg


@pytest.mark.parametrize('temp_dir', CLOUD_TEMP_FILESYSTEMS, ids=str)
def test_func_local_update_vzg_cloud(temp_dir: TempDir):
    test_func_local_update_vzg(temp_dir)
