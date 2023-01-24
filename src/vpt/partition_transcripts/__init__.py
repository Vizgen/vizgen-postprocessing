import argparse
from vpt.partition_transcripts.cmd_args import get_parser

# Prevent import from being removed as "unused"
assert get_parser


def run(args: argparse.Namespace):
    from vpt.partition_transcripts.run_partition_transcripts import main_partition_transcripts
    main_partition_transcripts(args)
