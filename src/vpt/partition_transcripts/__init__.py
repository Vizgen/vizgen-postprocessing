import argparse
import warnings

import pandas as pd

import vpt.partition_transcripts.cmd_args as cmd_args

get_parser = cmd_args.get_parser
warnings.simplefilter(action="ignore", category=pd.errors.PerformanceWarning)


def run(args: argparse.Namespace):
    from vpt.partition_transcripts.run_partition_transcripts import main_partition_transcripts

    main_partition_transcripts(args)
