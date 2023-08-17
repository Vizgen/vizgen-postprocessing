import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from tests.vpt import IMAGES_ROOT, OUTPUT_FOLDER
from tests.vpt.integration import DATA_ROOT as TEST_DATA_ROOT
from vpt.cmd_args import get_postprocess_parser as get_parser
from vpt.vizgen_postprocess import main as vpt_run
from vpt_core.io.input_tools import read_parquet
from vpt_core.segmentation.seg_result import SegmentationResult


@pytest.fixture
def output_folder() -> Path:
    with TemporaryDirectory(dir=OUTPUT_FOLDER) as td:
        yield Path(td)


def check_results(folder: Path) -> bool:
    spec = folder / "segmentation_specification.json"
    if not spec.exists():
        return False
    data = json.loads(spec.read_text())
    for of in data["segmentation_algorithm"]["output_files"]:
        if not (folder / of["files"]["run_on_tile_dir"]).exists():
            return False
        for entity in of["entity_types_output"]:
            if len(of["entity_types_output"]) > 1:
                if not (folder / f'{entity}_{of["files"]["micron_geometry_file"]}').exists():
                    return False
            else:
                if not (folder / of["files"]["micron_geometry_file"]).exists():
                    return False

    return True


def non_overlap(folder: Path):
    spec = folder / "segmentation_specification.json"
    data = json.loads(spec.read_text())
    for of in data["segmentation_algorithm"]["output_files"]:
        for entity in of["entity_types_output"]:
            if len(of["entity_types_output"]) > 1:
                seg_df = SegmentationResult(
                    dataframe=read_parquet(str(folder / f'{entity}_{of["files"]["mosaic_geometry_file"]}'))
                )
            else:
                seg_df = SegmentationResult(dataframe=read_parquet(str(folder / of["files"]["mosaic_geometry_file"])))

            assert len(seg_df.find_overlapping_entities(seg_df.df)) == 0


def test_run_prepare_segmentation_single_tile(output_folder: Path):
    vpt_run(
        get_parser().parse_args(
            [
                "--verbose",
                "prepare-segmentation",
                "--input-images",
                IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
                "--segmentation-algorithm",
                str(TEST_DATA_ROOT / "watershed_sd.json"),
                "--output-path",
                str(output_folder),
                "--input-micron-to-mosaic",
                str(TEST_DATA_ROOT / "uniform_matrix.csv"),
                "--tile-size",
                "428",
                "--overwrite",
            ]
        )
    )
    content = (output_folder / "segmentation_specification.json").read_text()
    data = json.loads(content)
    assert len(data["input_data"]["channels"]) == 2
    assert len(data["input_data"]["z_layers"]) == 7
    assert len(data["window_grid"]["windows"]) == 1


def test_run_prepare_segmentation_two_entities(output_folder: Path):
    vpt_run(
        get_parser().parse_args(
            [
                "prepare-segmentation",
                "--input-images",
                IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
                "--segmentation-algorithm",
                str(TEST_DATA_ROOT / "watershed_two_entities.json"),
                "--output-path",
                str(output_folder),
                "--input-micron-to-mosaic",
                str(TEST_DATA_ROOT / "uniform_matrix.csv"),
                "--tile-size",
                "250",
                "--overwrite",
            ]
        )
    )
    content = (output_folder / "segmentation_specification.json").read_text()
    data = json.loads(content)
    assert len(data["input_data"]["channels"]) == 2
    assert len(data["input_data"]["z_layers"]) == 7
    assert len(data["window_grid"]["windows"]) == 4


def test_run_prepare_segmentation_4tiles(output_folder: Path):
    vpt_run(
        get_parser().parse_args(
            [
                "prepare-segmentation",
                "--input-images",
                IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
                "--segmentation-algorithm",
                str(TEST_DATA_ROOT / "watershed_sd.json"),
                "--output-path",
                str(output_folder),
                "--input-micron-to-mosaic",
                str(TEST_DATA_ROOT / "uniform_matrix.csv"),
                "--tile-size",
                "205",
                "--tile-overlap",
                "51",
                "--overwrite",
            ]
        )
    )
    content = (output_folder / "segmentation_specification.json").read_text()
    data = json.loads(content)
    assert len(data["input_data"]["channels"]) == 2
    assert len(data["input_data"]["z_layers"]) == 7
    assert len(data["window_grid"]["windows"]) == 4


def test_run_segmentation_watershed_cell_4t(output_folder: Path):
    vpt_run(
        get_parser().parse_args(
            [
                "run-segmentation",
                "--input-images",
                IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
                "--segmentation-algorithm",
                str(TEST_DATA_ROOT / "watershed_sd.json"),
                "--output-path",
                str(output_folder),
                "--input-micron-to-mosaic",
                str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
                "--tile-size",
                "205",
                "--tile-overlap",
                "51",
                "--overwrite",
            ]
        )
    )
    assert check_results(output_folder)
    non_overlap(output_folder)


def test_run_segmentation_watershed_two_entities_4t(output_folder: Path):
    vpt_run(
        get_parser().parse_args(
            [
                "run-segmentation",
                "--input-images",
                IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
                "--segmentation-algorithm",
                str(TEST_DATA_ROOT / "watershed_two_entities.json"),
                "--output-path",
                str(output_folder),
                "--input-micron-to-mosaic",
                str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
                "--tile-size",
                "205",
                "--tile-overlap",
                "100",
                "--overwrite",
            ]
        )
    )
    assert check_results(output_folder)


def test_run_segmentation_watershed_cell_4t_4p(output_folder: Path):
    vpt_run(
        get_parser().parse_args(
            [
                "--log-file",
                str(output_folder / "log.txt"),
                "--processes",
                "4",
                "run-segmentation",
                "--input-images",
                IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
                "--segmentation-algorithm",
                str(TEST_DATA_ROOT / "watershed_sd.json"),
                "--output-path",
                str(output_folder),
                "--input-micron-to-mosaic",
                str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
                "--tile-size",
                "205",
                "--tile-overlap",
                "51",
                "--overwrite",
            ]
        )
    )
    assert check_results(output_folder)
    non_overlap(output_folder)


def test_run_segmentation_watershed_1t(output_folder: Path):
    vpt_run(
        get_parser().parse_args(
            [
                "--log-file",
                str(output_folder / "log.txt"),
                "run-segmentation",
                "--input-images",
                IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
                "--segmentation-algorithm",
                str(TEST_DATA_ROOT / "watershed_sd.json"),
                "--output-path",
                str(output_folder),
                "--input-micron-to-mosaic",
                str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
                "--tile-size",
                "428",
                "--overwrite",
            ]
        )
    )
    assert check_results(output_folder)
    non_overlap(output_folder)


def test_run_segmentation_watershed_nuclei_1t(output_folder: Path):
    vpt_run(
        get_parser().parse_args(
            [
                "run-segmentation",
                "--input-images",
                IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
                "--segmentation-algorithm",
                str(TEST_DATA_ROOT / "watershed_only_nucl.json"),
                "--output-path",
                str(output_folder),
                "--input-micron-to-mosaic",
                str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
                "--tile-size",
                "428",
                "--overwrite",
            ]
        )
    )
    assert check_results(output_folder)
    non_overlap(output_folder)


def test_run_segmentation_cp_1_4t(output_folder: Path):
    vpt_run(
        get_parser().parse_args(
            [
                "--processes",
                "4",
                "run-segmentation",
                "--input-images",
                IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
                "--segmentation-algorithm",
                str(TEST_DATA_ROOT / "cellpose_1.json"),
                "--output-path",
                str(output_folder),
                "--input-micron-to-mosaic",
                str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
                "--tile-size",
                "205",
                "--tile-overlap",
                "51",
                "--overwrite",
            ]
        )
    )
    assert check_results(output_folder)
    non_overlap(output_folder)


def test_run_segmentation_cp_1_1t(output_folder: Path):
    vpt_run(
        get_parser().parse_args(
            [
                "run-segmentation",
                "--input-images",
                IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
                "--segmentation-algorithm",
                str(TEST_DATA_ROOT / "cellpose_1.json"),
                "--output-path",
                str(output_folder),
                "--input-micron-to-mosaic",
                str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
                "--tile-size",
                "428",
                "--overwrite",
            ]
        )
    )
    assert check_results(output_folder)


def test_run_segmentation_cp_two_entities_4t(output_folder: Path):
    vpt_run(
        get_parser().parse_args(
            [
                "--processes",
                "4",
                "run-segmentation",
                "--input-images",
                IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
                "--segmentation-algorithm",
                str(TEST_DATA_ROOT / "cellpose_two_entities.json"),
                "--output-path",
                str(output_folder),
                "--input-micron-to-mosaic",
                str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
                "--tile-size",
                "205",
                "--tile-overlap",
                "50",
                "--overwrite",
            ]
        )
    )
    assert check_results(output_folder)


def test_run_segmentation_cp_two_entities_demo_data(output_folder: Path):
    vpt_run(
        get_parser().parse_args(
            [
                "run-segmentation",
                "--input-images",
                IMAGES_ROOT.as_posix() + r"_demo/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
                "--segmentation-algorithm",
                str(TEST_DATA_ROOT / "cellpose_two_entities.json"),
                "--output-path",
                str(output_folder),
                "--input-micron-to-mosaic",
                str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
                "--tile-size",
                "600",
                "--tile-overlap",
                "200",
                "--overwrite",
            ]
        )
    )
    assert check_results(output_folder)
