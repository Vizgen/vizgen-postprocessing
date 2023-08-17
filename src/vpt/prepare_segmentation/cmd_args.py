from argparse import ArgumentParser
from dataclasses import dataclass

from vpt_core.io.vzgfs import filesystem_path_split

from vpt.prepare_segmentation.constants import OUTPUT_FILE_NAME
from vpt.utils.validate import validate_does_not_exist, validate_exists


@dataclass(frozen=True)
class PrepareSegmentationArgs:
    segmentation_algorithm: str
    input_images: str
    input_micron_to_mosaic: str
    tile_size: int
    tile_overlap: int
    output_path: str
    overwrite: bool


def validate_prepare_segmentation_args(args: PrepareSegmentationArgs):
    validate_exists(args.input_micron_to_mosaic)

    if args.tile_size <= 0:
        raise ValueError("Tile size should be positive")
    if args.tile_overlap < 0 or args.tile_overlap > args.tile_size:
        raise ValueError("Tile overlap should be in [0, tile-size] range")

    if not args.overwrite:
        fs, path_inside_fs = filesystem_path_split(args.output_path)
        if fs.exists(path_inside_fs):
            validate_does_not_exist(args.output_path + "/" + OUTPUT_FILE_NAME)


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Generates a segmentation specification json file to be used for cell segmentation "
        "tasks. The segmentation specification json includes specification for the algorithm to run, "
        "the paths for all images for each stain for each z index, the micron to mosaic pixel "
        "transformation matrix, the number of tiles, and the window coordinates for each tile.",
        add_help=False,
    )

    required = parser.add_argument_group("Required arguments")
    required.add_argument(
        "--segmentation-algorithm",
        type=str,
        required=True,
        help="Path to a json file that fully specifies the segmentation algorithm to use, "
        "including algorithm name, any algorithm specific parameters "
        "(including path to weights for new model), stains corresponding to each channel "
        "in the algorithm.",
    )
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
        "--output-path",
        type=str,
        required=True,
        help="Path where the segmentation specification json file will be saved.",
    )
    required.add_argument(
        "--input-micron-to-mosaic",
        type=str,
        required=True,
        help="Path to the micron to mosaic pixel transformation matrix.",
    )

    opt = parser.add_argument_group("Optional arguments")
    opt.add_argument(
        "--tile-size",
        type=int,
        default=4096,
        help="Number of pixels for the width and height of each tile. "
        "Each tile is created as a square. Default is 4096.",
    )
    opt.add_argument(
        "--tile-overlap", type=int, required=False, help="Overlap between adjacent tiles. Default is 10%% of tile-size."
    )
    opt.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        required=False,
        help="Set flag if you want to use non empty directory and agree that files can be over-written.",
    )
    opt.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    return parser


def parse_args():
    return get_parser().parse_args()
