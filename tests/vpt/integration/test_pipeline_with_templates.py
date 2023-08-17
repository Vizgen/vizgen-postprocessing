from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from tests.vpt import IMAGES_ROOT, OUTPUT_FOLDER
from tests.vpt.integration import DATA_ROOT as TEST_DATA_ROOT
from vpt.cmd_args import get_postprocess_parser as get_parser
from vpt.utils.seg_json_generator.cmd_args import get_parser as gen_parser
from vpt.utils.seg_json_generator.main import run_generator
from vpt.vizgen_postprocess import main as vpt_run


@pytest.fixture
def output_folder() -> Path:
    with TemporaryDirectory(dir=OUTPUT_FOLDER) as td:
        yield Path(td)


def test_merlin_watershed(output_folder: Path) -> None:
    alg = str(output_folder / "algorithm.json")
    run_generator(
        gen_parser().parse_args(
            ["--input-analysis-spec", str(TEST_DATA_ROOT / "template_params.json"), "--output-path", alg, "--overwrite"]
        )
    )
    vpt_run(
        get_parser().parse_args(
            [
                "--log-file",
                str(output_folder / "log.txt"),
                "run-segmentation",
                "--input-images",
                IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
                "--segmentation-algorithm",
                alg,
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
    assert (output_folder / "micron_space.parquet").exists()
    assert (output_folder / "mosaic_space.parquet").exists()
