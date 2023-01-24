import argparse
from vpt.sum_signals.cmd_args import get_parser

# Assert so not flagged as unused
assert get_parser


def run(args: argparse.Namespace):
    from vpt.sum_signals.main import sum_signals
    sum_signals(args)
