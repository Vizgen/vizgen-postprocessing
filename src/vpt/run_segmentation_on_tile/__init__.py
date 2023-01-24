import argparse
from vpt.run_segmentation_on_tile.cmd_args import get_parser

# Prevent import from being removed as "unused"
assert get_parser


def run(args: argparse.Namespace):
    from vpt.run_segmentation_on_tile.main import run_segmentation_on_tile
    run_segmentation_on_tile(args)
