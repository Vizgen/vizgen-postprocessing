import argparse
from vpt.derive_cell_metadata.cmd_args import get_parser

# Prevent import from being removed as "unused"
assert get_parser


def run(args: argparse.Namespace):
    from vpt.derive_cell_metadata.run_derive_cell_metadata import main_derive_cell_metadata
    main_derive_cell_metadata(args)
