import pytest
from vpt_core.io.vzgfs import initialize_filesystem

from tests.vpt.integration_cloud import CLOUD_TEMP_FILESYSTEMS
from tests.vpt.temp_dir import TempDir
from tests.vpt.test_partition_barcodes import (
    test_func_partition_barcodes,
    test_func_partition_barcodes_new_transcripts,
    test_no_cells,
)


@pytest.mark.parametrize("temp_dir", CLOUD_TEMP_FILESYSTEMS, ids=str)
def test_func_partition_barcodes_cloud(temp_dir: TempDir):
    initialize_filesystem()
    test_func_partition_barcodes(temp_dir)


@pytest.mark.parametrize("temp_dir", CLOUD_TEMP_FILESYSTEMS, ids=str)
def test_func_partition_barcodes_new_transcripts_cloud(temp_dir: TempDir):
    initialize_filesystem()
    test_func_partition_barcodes_new_transcripts(temp_dir)


@pytest.mark.parametrize("temp_dir", CLOUD_TEMP_FILESYSTEMS, ids=str)
def test_no_cells_cloud(temp_dir: TempDir):
    initialize_filesystem()
    test_no_cells(temp_dir)
