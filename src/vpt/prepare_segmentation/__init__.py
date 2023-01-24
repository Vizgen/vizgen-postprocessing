import argparse
from vpt.prepare_segmentation.cmd_args import get_parser

# Prevent import from being removed as "unused"
assert get_parser


def run(args: argparse.Namespace):
    from vpt.prepare_segmentation.main import run_prepare_segmentation
    run_prepare_segmentation(args)
