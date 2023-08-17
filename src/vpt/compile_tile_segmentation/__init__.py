import argparse

import vpt.compile_tile_segmentation.cmd_args as cmd_args

get_parser = cmd_args.get_parser


def run(args: argparse.Namespace):
    from vpt.compile_tile_segmentation.main import compile_tile_segmentation

    compile_tile_segmentation(args)
