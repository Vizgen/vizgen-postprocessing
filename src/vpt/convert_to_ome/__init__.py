import argparse

import vpt.convert_to_ome.cmd_args as cmd_args
import vpt.convert_to_ome.rgb_cmd_args as rgb_cmd_args

get_parser = cmd_args.get_parser
get_parser_rgb = rgb_cmd_args.get_parser


def run_ome(args: argparse.Namespace):
    from vpt.convert_to_ome.main import convert_to_ome

    convert_to_ome(args)


def run_ome_rgb(args: argparse.Namespace):
    from vpt.convert_to_ome.main_rgb import convert_to_ome_rgb

    convert_to_ome_rgb(args)
