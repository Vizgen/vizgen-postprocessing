import argparse
from vpt.compile_tile_segmentation.cmd_args import get_parser

# Prevent import from being removed as "unused"
assert get_parser


def run(args: argparse.Namespace):
    from vpt.compile_tile_segmentation.main import compile_tile_segmentation
    compile_tile_segmentation(args)
