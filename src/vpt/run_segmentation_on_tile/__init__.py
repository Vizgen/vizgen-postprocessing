import argparse

from vpt.run_segmentation_on_tile.cmd_args import get_parser as parser

get_parser = parser


def run(args: argparse.Namespace):
    from vpt.run_segmentation_on_tile.main import run_segmentation_on_tile

    run_segmentation_on_tile(args)
