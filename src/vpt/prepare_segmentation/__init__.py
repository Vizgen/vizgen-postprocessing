import argparse

import vpt.prepare_segmentation.cmd_args as cmd_args

get_parser = cmd_args.get_parser


def run(args: argparse.Namespace):
    from vpt.prepare_segmentation.main import run_prepare_segmentation

    run_prepare_segmentation(args)
