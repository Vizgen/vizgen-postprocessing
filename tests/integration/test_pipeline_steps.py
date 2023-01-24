import json

from tests import IMAGES_ROOT, OUTPUT_FOLDER, TEST_DATA_ROOT
from vpt.vizgen_postprocess import main as vpt_run
from vpt.cmd_args import get_postprocess_parser as get_parser


def test_run_prepare_segmentation_single_tile():
    vpt_run(get_parser().parse_args(
        [
            "prepare-segmentation",
            "--input-images", IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
            "--segmentation-algorithm", str(TEST_DATA_ROOT / "watershed_sd.json"),
            "--output-path", str(OUTPUT_FOLDER),
            "--input-micron-to-mosaic", str(TEST_DATA_ROOT / "uniform_matrix.csv"),
            "--tile-size", "428",
            "--overwrite"
        ]))
    content = (OUTPUT_FOLDER / 'segmentation_specification.json').read_text()
    data = json.loads(content)
    assert len(data['input_data']['channels']) == 2
    assert len(data['input_data']['z_layers']) == 7
    assert len(data['window_grid']['windows']) == 1


def test_run_prepare_segmentation_4tiles():
    vpt_run(get_parser().parse_args(
        [
            "prepare-segmentation",
            "--input-images", IMAGES_ROOT.as_posix() + r'/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif',
            "--segmentation-algorithm", str(TEST_DATA_ROOT / "watershed_sd.json"),
            "--output-path", str(OUTPUT_FOLDER),
            "--input-micron-to-mosaic", str(TEST_DATA_ROOT / "uniform_matrix.csv"),
            "--tile-size", "205",
            "--tile-overlap", "51",
            "--overwrite"
        ]))
    content = (OUTPUT_FOLDER / 'segmentation_specification.json').read_text()
    data = json.loads(content)
    assert len(data['input_data']['channels']) == 2
    assert len(data['input_data']['z_layers']) == 7
    assert len(data['window_grid']['windows']) == 4


def test_run_segmentation_watershed_cell_4t():
    vpt_run(get_parser().parse_args(
        [
            "run-segmentation",
            "--input-images", IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
            "--segmentation-algorithm", str(TEST_DATA_ROOT / "watershed_sd.json"),
            "--output-path", str(OUTPUT_FOLDER),
            "--input-micron-to-mosaic", str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
            "--tile-size", "205",
            "--tile-overlap", "51",
            "--overwrite"
        ]))


def test_run_segmentation_watershed_cell_4t_4p():
    vpt_run(get_parser().parse_args(
        [
            "--log-file", str(OUTPUT_FOLDER / 'log.txt'),
            "--processes", "4",
            "run-segmentation",
            "--input-images", IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
            "--segmentation-algorithm", str(TEST_DATA_ROOT / "watershed_sd.json"),
            "--output-path", str(OUTPUT_FOLDER),
            "--input-micron-to-mosaic", str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
            "--tile-size", "205",
            "--tile-overlap", "51",
            "--overwrite"
        ]))


def test_run_segmentation_watershed_1t():
    vpt_run(get_parser().parse_args(
        [
            "--log-file", str(OUTPUT_FOLDER / 'log.txt'),
            "run-segmentation",
            "--input-images", IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
            "--segmentation-algorithm", str(TEST_DATA_ROOT / "watershed_sd.json"),
            "--output-path", str(OUTPUT_FOLDER),
            "--input-micron-to-mosaic", str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
            "--tile-size", "428",
            "--overwrite"
        ]))


def test_run_segmentation_watershed_nuclei_1t():
    vpt_run(get_parser().parse_args(
        [
            "run-segmentation",
            "--input-images", IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
            "--segmentation-algorithm", str(TEST_DATA_ROOT / "watershed_only_nucl.json"),
            "--output-path", str(OUTPUT_FOLDER),
            "--input-micron-to-mosaic", str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
            "--tile-size", "428",
            "--overwrite"
        ]))


def test_run_segmentation_cp_1_4t():
    vpt_run(get_parser().parse_args(
        [
            "--processes", "4",
            "run-segmentation",
            "--input-images", IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
            "--segmentation-algorithm", str(TEST_DATA_ROOT / "cellpose_1.json"),
            "--output-path", str(OUTPUT_FOLDER),
            "--input-micron-to-mosaic", str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
            "--tile-size", "205",
            "--tile-overlap", "51",
            "--overwrite"
        ]))


def test_run_segmentation_cp_1_1t():
    vpt_run(get_parser().parse_args(
        [
            "run-segmentation",
            "--input-images", IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
            "--segmentation-algorithm", str(TEST_DATA_ROOT / "cellpose_1.json"),
            "--output-path", str(OUTPUT_FOLDER),
            "--input-micron-to-mosaic", str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
            "--tile-size", "428",
            "--overwrite"
        ]))
