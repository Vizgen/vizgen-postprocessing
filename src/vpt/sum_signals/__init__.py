import argparse

import vpt.sum_signals.cmd_args as cmd_args

get_parser = cmd_args.get_parser


def run(args: argparse.Namespace):
    from vpt.sum_signals.main import sum_signals

    sum_signals(args)
