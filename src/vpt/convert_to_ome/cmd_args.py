from argparse import ArgumentParser
from dataclasses import dataclass

from vpt_core.io.vzgfs import filesystem_path_split

from vpt.utils.validate import validate_does_not_exist, validate_exists


@dataclass
class ConvertToOmeArgs:
    input_path: str
    output_path: str
    overwrite: bool


def validate_args(args: ConvertToOmeArgs):
    input_fs, input_path_inside_fs = filesystem_path_split(args.input_path)
    output_fs, output_path_inside_fs = filesystem_path_split(args.output_path)

    validate_exists(args.input_path)

    if input_fs.isdir(input_path_inside_fs):
        if output_fs.isfile(output_path_inside_fs):
            raise ValueError("Output path should be a directory since the provided input path is a directory")
        if not args.overwrite:
            for path in input_fs.glob(input_fs.sep.join([input_path_inside_fs, "*.tif"])):
                stem = path.split(input_fs.sep)[-1].split(".")[0]
                output_file = output_fs.sep.join([output_path_inside_fs, f"{stem}.ome.tif"])
                if output_fs.exists(output_file):
                    raise ValueError(f"Output file already exists: {output_file}")

    if input_fs.isfile(input_path_inside_fs):
        if output_fs.isdir(output_path_inside_fs):
            raise ValueError("Output path should be a file since the provided input path is a file")
        if not args.overwrite:
            validate_does_not_exist(args.output_path)


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Transforms the large 16-bit mosaic tiff images produced by the MERSCOPE "
        "into a OME pyramidal tiff.",
        add_help=False,
    )
    required = parser.add_argument_group("Required arguments")
    required.add_argument(
        "--input-image", type=str, required=True, help="Either a path to a directory or a path to a specific file."
    )

    opt = parser.add_argument_group("Optional arguments")
    opt.add_argument(
        "--output-image", type=str, required=True, help="Either a path to a directory or a path to a specific file."
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
