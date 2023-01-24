import argparse
from vpt.convert_geometry.cmd_args import get_parser

# Prevent import from being removed as "unused"
assert get_parser


def run_conversion(args: argparse.Namespace):
    from vpt.convert_geometry.main import convert_geometry
    convert_geometry(args)
