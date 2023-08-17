import argparse

import vpt.convert_geometry.cmd_args as cmd_args

get_parser = cmd_args.get_parser


def run_conversion(args: argparse.Namespace):
    from vpt.convert_geometry.main import convert_geometry

    convert_geometry(args)
