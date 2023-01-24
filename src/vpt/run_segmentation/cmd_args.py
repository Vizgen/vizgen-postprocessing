from argparse import ArgumentParser
from dataclasses import dataclass

from vpt.filesystem import filesystem_path_split
from vpt.prepare_segmentation.constants import OUTPUT_FILE_NAME
from vpt.utils.output_tools import MIN_ROW_GROUP_SIZE
from vpt.utils.validate import validate_exists, validate_does_not_exist

# The maximum number of parallel processes that may be launched by run-segmentation
MAX_PROCESSES = 512


@dataclass
class RunSegmentationArgs:
    segmentation_algorithm: str
    input_images: str
    input_micron_to_mosaic: str
    tile_size: int
    tile_overlap: int
    output_path: str
    max_row_group_size: int
    overwrite: bool


def validate_args(args: RunSegmentationArgs):
    validate_exists(args.input_micron_to_mosaic)

    if args.tile_size <= 0:
        raise ValueError('Tile size should be positive')
    if args.tile_overlap is not None:
        if args.tile_overlap < 0 or args.tile_overlap > args.tile_size:
            raise ValueError('Tile overlap should be in [0, tile-size] range')

    if args.max_row_group_size < MIN_ROW_GROUP_SIZE:
        raise ValueError(f'Row group size should be at least {MIN_ROW_GROUP_SIZE}')

    if not args.overwrite:
        fs, path_inside_fs = filesystem_path_split(args.output_path)
        if fs.exists(path_inside_fs):
            validate_does_not_exist(args.output_path + '/' + OUTPUT_FILE_NAME)


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(description='Top-level interface for this CLI which invokes the segmentation '
                            'functionality of the tool. It is intended for users who would like to run '
                            'the program with minimal additional configuration. Specifically, it executes: '
                            'prepare-segmentation, run-segmentation-on-tile, and compile-tile-segmentation.',
                            add_help=False
                            )

    required = parser.add_argument_group('Required arguments')
    required.add_argument('--segmentation-algorithm', type=str, required=True,
                          help='Path to a json file that fully specifies the segmentation algorithm to use, '
                               'including algorithm name, any algorithm specific parameters '
                               '(including path to weights for new model), stains corresponding to each channel '
                               'in the algorithm.')
    required.add_argument('--input-images', type=str, required=True,
                          help=r'Regular expression containing path that indicates the images to use '
                               r'for the segmentation. The regular expressions can indicate the z index '
                               r'(indicated by (?P<z>[0-9]+)) and/or multiple stains (indicated by (?P<stain>[\w|-]+)). '
                               r'Here, <stain> must match the stains specified in the segmentation algorithm.')
    required.add_argument('--input-micron-to-mosaic', type=str, required=True,
                          help='Path to the micron to mosaic pixel transformation matrix.')
    required.add_argument('--output-path', type=str, required=True,
                          help='Directory where the segmentation specification json file '
                               'will be saved as segmentation_specification.json and where '
                               'the final segmentation results will be saved.')

    opt = parser.add_argument_group('Optional arguments')
    opt.add_argument('--tile-size', type=int, default=4096,
                     help='Number of pixels for the width and height of each tile. '
                          'Each tile is created as a square. Default: 4096.')
    opt.add_argument('--tile-overlap', type=int, required=False,
                     help='Overlap between adjacent tiles. Default: 10%% of tile size.')
    opt.add_argument('--max-row-group-size', type=int, default=17500, required=False,
                     help='Maximum number of rows in row groups inside output parquet files. '
                          f'Cannot be less than {MIN_ROW_GROUP_SIZE}')
    opt.add_argument('--overwrite', action='store_true', default=False, required=False,
                     help='Set flag if you want to use non empty directory and agree that files can be over-written.')
    opt.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    return parser
