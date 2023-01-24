from argparse import ArgumentParser
from dataclasses import dataclass
from typing import Dict

from vpt.segmentation.utils.seg_result import SegmentationResult
from vpt.utils.validate import validate_exists


@dataclass
class RunOnTileCmdArgs:
    input_segmentation_parameters: str
    tile_index: int
    overwrite: bool


def validate_cmd_args(args: RunOnTileCmdArgs):
    validate_exists(args.input_segmentation_parameters)

    if args.tile_index < 0:
        raise ValueError('Tile index should be a positive integer')

    if args.tile_index > SegmentationResult.MAX_TILE_ID:
        raise ValueError(f'Tile index should be less than {SegmentationResult.MAX_TILE_ID}')


def get_parser():
    parser = ArgumentParser(description='Executes the segmentation algorithm on a specific tile '
                            'of the mosaic images. This functionality is intended both for visualizing '
                            'a preview of the segmentation (run only one tile), and for distributing '
                            'jobs using an orchestration tool such as Nextflow.',
                            add_help=False
                            )

    required = parser.add_argument_group('Required arguments')
    required.add_argument('--input-segmentation-parameters', type=str, required=True,
                          help='Json file generate by --prepare-segmentation that fully '
                               'specifies the segmentation to run')
    required.add_argument('--tile-index', type=int, required=True,
                          help='Index of the tile to run the segmentation on')

    opt = parser.add_argument_group('Optional arguments')
    opt.add_argument('--overwrite', action='store_true', default=False, required=False,
                     help='Set flag if you want to use non empty directory and agree that files can be over-written.')
    opt.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    return parser


def parse_cmd_args() -> Dict:
    parser = get_parser()
    namespace = parser.parse_args()
    return vars(namespace)
