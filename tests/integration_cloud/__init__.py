from tests.temp_dir import CloudTempDir
from vpt.filesystem import initialize_filesystem

TEST_S3_BUCKET_PATH = 's3://vpt-aws-test/temp_dir_cloud'
TEST_GCS_PATH = 'gcs://vpt-gs-test/temp_dir_cloud'

initialize_filesystem()

CLOUD_TEMP_FILESYSTEMS = [CloudTempDir(TEST_S3_BUCKET_PATH), CloudTempDir(TEST_GCS_PATH)]
