import argparse
from vpt.convert_to_ome.cmd_args import get_parser
from vpt.convert_to_ome.rgb_cmd_args import get_parser as get_parser_rgb

# Prevent imports from being removed as "unused"
assert get_parser
assert get_parser_rgb


def run_ome(args: argparse.Namespace):
    from vpt.convert_to_ome.main import convert_to_ome
    convert_to_ome(args)


def run_ome_rgb(args: argparse.Namespace):
    from vpt.convert_to_ome.main_rgb import convert_to_ome_rgb
    convert_to_ome_rgb(args)
