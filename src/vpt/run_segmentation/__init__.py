import argparse

import vpt.run_segmentation.cmd_args as cmd_args

get_parser = cmd_args.get_parser


def run(args: argparse.Namespace):
    from vpt.run_segmentation.main import run_segmentation

    run_segmentation(args)
