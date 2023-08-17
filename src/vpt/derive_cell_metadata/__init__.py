import argparse
import vpt.derive_cell_metadata.cmd_args as cmd_args

get_parser = cmd_args.get_parser


def run(args: argparse.Namespace):
    from vpt.derive_cell_metadata.run_derive_cell_metadata import main_derive_cell_metadata

    main_derive_cell_metadata(args)
