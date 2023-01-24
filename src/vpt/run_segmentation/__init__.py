import argparse
from vpt.run_segmentation.cmd_args import get_parser

# Prevent import from being removed as "unused"
assert get_parser


def run(args: argparse.Namespace):
    from vpt.run_segmentation.main import run_segmentation
    run_segmentation(args)
