import argparse

import vpt.generate_segmentation_metrics.cmd_args as cmd_args

get_parser = cmd_args.get_parser


def run(args: argparse.Namespace):
    from vpt.generate_segmentation_metrics.main import generate_segmentation_metrics

    generate_segmentation_metrics(args)
