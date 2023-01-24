from argparse import ArgumentParser
from dataclasses import dataclass
from typing import Optional

from vpt.filesystem import filesystem_path_split
from vpt.utils.validate import validate_does_not_exist


@dataclass
class ConvertToRGBOmeArgs:
    input_path_red: Optional[str]
    input_path_green: Optional[str]
    input_path_blue: Optional[str]
    output_path: str
    overwrite: bool


def validate_args(args: ConvertToRGBOmeArgs):
    if all(path is None for path in (args.input_path_red,
                                     args.input_path_green,
                                     args.input_path_blue)):
        raise ValueError('Image for least one of the channels should be specified')

    for input_path in args.input_path_red, args.input_path_green, args.input_path_blue:
        if input_path is None:
            continue

        input_fs, input_path_inside_fs = filesystem_path_split(input_path)

        if not input_fs.isfile(input_path_inside_fs):
            raise ValueError(f'Input is not a file: {input_path}')

    output_fs, output_path_inside_fs = filesystem_path_split(args.output_path)

    if output_fs.isdir(output_path_inside_fs):
        raise ValueError('Output should be a file')

    if not args.overwrite:
        validate_does_not_exist(args.output_path)


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(description='Converts up to three flat tiff images into a rgb OME-tiff pyramidal images. '
                            'If a rgb channel input isn’t specified, the channel will be dark (all 0’s).',
                            add_help=False
                            )
    required = parser.add_argument_group('Required arguments')
    required.add_argument('--output-image', type=str, required=True,
                          help='Either a path to a directory or a path to a specific file')

    opt = parser.add_argument_group('Optional arguments')
    opt.add_argument('--input-image-red', type=str, required=False,
                     help='Either a path to a directory or a path to a specific file')
    opt.add_argument('--input-image-green', type=str, required=False,
                     help='Either a path to a directory or a path to a specific file')
    opt.add_argument('--input-image-blue', type=str, required=False,
                     help='Either a path to a directory or a path to a specific file')
    opt.add_argument('--overwrite', action='store_true', default=False, required=False,
                     help='')
    opt.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    return parser
