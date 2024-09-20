import pytest

from tests.vpt.integration_cloud import CLOUD_TEMP_FILESYSTEMS
from tests.vpt.temp_dir import TempDir
from tests.vpt.test_update_vzg import test_func_local_update_vzg, test_two_features_local_update_vzg


@pytest.mark.parametrize("vzg2", [True, False], ids=str)
@pytest.mark.parametrize("temp_dir", CLOUD_TEMP_FILESYSTEMS, ids=str)
def test_func_local_update_vzg_cloud(temp_dir: TempDir, vzg2: bool):
    test_func_local_update_vzg(temp_dir, vzg2)


@pytest.mark.parametrize("vzg2", [True, False], ids=str)
@pytest.mark.parametrize("temp_dir", CLOUD_TEMP_FILESYSTEMS, ids=str)
def test_two_features_local_update_vzg_cloud(temp_dir: TempDir, vzg2: bool):
    test_two_features_local_update_vzg(temp_dir, vzg2)
