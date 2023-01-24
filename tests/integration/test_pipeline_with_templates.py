from tests import IMAGES_ROOT, OUTPUT_FOLDER, TEST_DATA_ROOT
from vpt.vizgen_postprocess import main as vpt_run
from vpt.cmd_args import get_postprocess_parser as get_parser
from vpt.utils.seg_json_generator.main import run_generator
from vpt.utils.seg_json_generator.cmd_args import get_parser as gen_parser


def test_merlin_watershed() -> None:
    out_dir = OUTPUT_FOLDER / 'test_merlin_watershed'
    out_dir.mkdir(exist_ok=True)
    alg = str(out_dir / 'algorithm.json')
    run_generator(gen_parser().parse_args([
        '--input-analysis-spec', str(TEST_DATA_ROOT / 'template_params.json'),
        '--output-path', alg,
        '--overwrite'
    ]
    ))
    vpt_run(get_parser().parse_args(
        [
            "--log-file", str(out_dir / 'log.txt'),
            "run-segmentation",
            "--input-images", IMAGES_ROOT.as_posix() + r"/mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif",
            "--segmentation-algorithm", alg,
            "--output-path", str(out_dir),
            "--input-micron-to-mosaic", str(TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv"),
            "--tile-size", "428",
            "--overwrite"
        ]))
