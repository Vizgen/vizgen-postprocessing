import pytest

from tests import IMAGES_ROOT, TEST_DATA_ROOT
from tests.integration_cloud import CLOUD_TEMP_FILESYSTEMS
from tests.temp_dir import TempDir
from tests.utils import _copy_between_filesystems, _copy_regex_images
from vpt.filesystem import initialize_filesystem
from vpt.vizgen_postprocess import main as vpt_run
from vpt.cmd_args import get_postprocess_parser as get_parser


@pytest.mark.parametrize('temp_dir', CLOUD_TEMP_FILESYSTEMS, ids=str)
def test_run_segmentation_watershed_cloud(temp_dir: TempDir):
    initialize_filesystem()
    path = temp_dir.get_temp_path()
    sep = temp_dir.get_sep()

    input_images = sep.join([path, r"mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif"])
    segmentation_algorithm = sep.join([path, "watershed_sd.json"])
    output_path = sep.join([path, "output"])
    m2m_path = sep.join([path, "micron_to_mosaic_pixel_transform.csv"])

    try:
        _copy_regex_images(IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
                           path, sep)

        _copy_between_filesystems(str(TEST_DATA_ROOT / "watershed_sd.json"), segmentation_algorithm)
        _copy_between_filesystems(str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"), m2m_path)

        vpt_run(get_parser().parse_args(
            [
                "run-segmentation",
                "--input-images", input_images,
                "--segmentation-algorithm", segmentation_algorithm,
                "--output-path", output_path,
                "--input-micron-to-mosaic", m2m_path,
                "--tile-size", "205",
                "--tile-overlap", "51",
                "--overwrite"
            ]))
    finally:
        temp_dir.clear_dir()
