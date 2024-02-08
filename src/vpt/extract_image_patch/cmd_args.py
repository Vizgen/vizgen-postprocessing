from argparse import ArgumentParser
from dataclasses import dataclass

from vpt.utils.validate import validate_does_not_exist, validate_exists


@dataclass
class ExtractImagePatchArgs:
    input_images: str
    input_micron_to_mosaic: str
    center_x: float
    center_y: float
    output_patch: str
    size_x: float
    size_y: float
    input_z_index: int
    red_stain_name: str
    green_stain_name: str
    blue_stain_name: str
    normalization: str
    overwrite: bool


def validate_args(args: ExtractImagePatchArgs):
    validate_exists(args.input_micron_to_mosaic)

    if args.size_x < 0 or args.size_y < 0:
        raise ValueError("Patch size needs to be > 0 in each dimension")
    if args.input_z_index < 0:
        raise ValueError("Z index needs to be >= 0")

    acceptable_filters = ["none", "range", "clahe"]
    if args.normalization.lower() not in acceptable_filters:
        raise ValueError(f"{args.normalization} is not currently a supported normalization type")

    if not args.overwrite:
        validate_does_not_exist(args.output_patch)


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Extracts a patch of specified coordinates and channels "
        "from the 16-bit mosaic tiff images produced by the MERSCOPE as "
        "an 8-bit RGB PNG file",
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
        "--input-micron-to-mosaic",
        type=str,
        required=True,
        help="Path to the micron to mosaic pixel transformation matrix.",
    )
    required.add_argument(
        "--output-patch",
        type=str,
        required=True,
        help="Path to the patch PNG file, will append .png to the end if not included in file name.",
    )
    required.add_argument(
        "--center-x",
        type=float,
        required=True,
        help="MERSCOPE Vizualizer X coordinate in micron space that will serve as the center of the saved PNG patch",
    )
    required.add_argument(
        "--center-y",
        type=float,
        required=True,
        help="MERSCOPE Vizualizer Y coordinate in micron space that will serve as the center of the saved PNG patch",
    )
    required.add_argument(
        "--green-stain-name",
        type=str,
        required=True,
        help="The name of the stain that will be used for the green channel of the patch",
    )

    opt = parser.add_argument_group("Optional arguments")
    opt.add_argument(
        "--size-x",
        type=float,
        default=108,
        help="Number of microns for the width of the patch. Default: 108.",
    )
    opt.add_argument(
        "--size-y",
        type=float,
        default=108,
        help="Number of microns for the height of the patch. Default: 108.",
    )
    opt.add_argument(
        "--input-z-index",
        type=int,
        default=2,
        help="The Z plane of the mosaic tiff images to use for the patch. Default: 2.",
    )
    opt.add_argument(
        "--red-stain-name",
        type=str,
        default=None,
        help="The name of the stain that will be used for the red channel of the patch. Default: None.",
    )
    opt.add_argument(
        "--blue-stain-name",
        type=str,
        default=None,
        help="The name of the stain that will be used for the blue channel of the patch. Default: None.",
    )
    opt.add_argument(
        "--normalization",
        type=str,
        default="CLAHE",
        help="The name of the normalization method that will be used on each channel of the patch. Default: None.",
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
