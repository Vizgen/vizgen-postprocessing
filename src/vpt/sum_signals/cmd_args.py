from argparse import ArgumentParser
from dataclasses import dataclass

from vpt.utils.validate import validate_does_not_exist, validate_exists

# The maximum number of parallel processes that may be launched by sum-signals
MAX_PROCESSES = 512


@dataclass
class SumSignalsArgs:
    input_images: str
    input_boundaries: str
    input_micron_to_mosaic: str
    output_csv: str
    overwrite: bool


def validate_args(args: SumSignalsArgs):
    validate_exists(args.input_boundaries)
    validate_exists(args.input_micron_to_mosaic)

    if not args.overwrite:
        validate_does_not_exist(args.output_csv)


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Uses the segmentation boundaries to find the intensity of each "
        "mosaic image in each Entity. Outputs both the summed intensity of the raw "
        "images and the summed intensity of high-pass filtered images (reduces the "
        "effect of background fluorescence).",
        add_help=False,
    )

    required = parser.add_argument_group("Required arguments")
    required.add_argument(
        "--input-images",
        type=str,
        required=True,
        help="Input images can be specified in one of three ways: 1. The path to a directory of tiff files, "
        "if the files are named by the MERSCOPE convention. Example: /path/to/files/ 2. The path to a "
        "directory of tiff files including a python formatting string specifying the file name. The "
        'format string must specify values for "stain" and "z". Example: '
        "/path/to/files/image_{stain}_z{z}.tif 3. A regular expression matching the tiff files to be "
        'used, where the regular expression specifies values for "stain" and "z". Example: '
        r"/path/to/files/mosaic_(?P<stain>[\w|-]+)_z(?P<z>[0-9]+).tif In all cases, the values for "
        '"stain" and "z" must match the stains and z indexes specified in the segmentation algorithm.',
    )
    required.add_argument(
        "--input-boundaries", type=str, required=True, help="Path to a micron-space .parquet boundary file."
    )
    required.add_argument(
        "--input-micron-to-mosaic",
        type=str,
        required=True,
        help="Path to the micron to mosaic pixel transformation matrix.",
    )
    required.add_argument(
        "--output-csv", type=str, required=True, help="Path to the csv file where the sum intensities will be stored."
    )

    opt = parser.add_argument_group("Optional arguments")
    opt.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        required=False,
        help="Set true if you want to use non empty directory and agree that files can be overwritten.",
    )
    opt.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    return parser


def parse_args():
    return get_parser().parse_args()
