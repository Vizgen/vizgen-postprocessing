import argparse

import vpt.update_vzg.cmd_args as cmd_args

get_parser = cmd_args.get_parser


def run(args: argparse.Namespace):
    from vpt.update_vzg.run_update_vzg import main_update_vzg

    main_update_vzg(args)


version_d = {"Major": 1, "Minor": 0, "Patch": 9}

version = "".join([str(version_d["Major"]), ".", str(version_d["Minor"]), ".", str(version_d["Patch"])])
