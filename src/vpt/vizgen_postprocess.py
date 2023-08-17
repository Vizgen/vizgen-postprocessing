import argparse
import sys
import traceback
import warnings
from argparse import Namespace
from typing import Dict, Tuple

from rasterio.errors import NotGeoreferencedWarning

from vpt.utils.metadata import get_installed_versions
from vpt_core import log

from vpt.app.context import Context
from vpt.cmd_args import get_cmd_entrypoint

warnings.filterwarnings("ignore", message=".*initial implementation of Parquet.*")
warnings.filterwarnings("ignore", message=".*invalid value encountered in intersection.*")
warnings.filterwarnings("ignore", message=".*pandas.Int64Index is deprecated.*")  # geopandas
warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)


# we need this function as a root of profile stats
def run_command(cmd: str, args: Namespace):
    log.info(f"run {cmd} with args:{args}")
    installed_versions = [f"{key} {val}" for key, val in get_installed_versions().items()]
    log.info("\n".join(["installed versions:", *installed_versions]))
    get_cmd_entrypoint(cmd)(args)


def split_args(parsed: argparse.Namespace) -> Tuple[Dict, argparse.Namespace]:
    # copy
    parsed = Namespace(**vars(parsed))
    ctx_args = {
        "dask_args": {
            "workers": parsed.processes,
        },
        "log_args": {
            "fname": parsed.log_file,
            "lvl": parsed.log_level,
            "verbose": parsed.verbose,
        },
        "prof_args": {"profile_file": parsed.profile_execution_time},
        "fs_args": {
            "aws_profile_name": parsed.aws_profile_name,
            "aws_access_key": parsed.aws_access_key,
            "aws_secret_key": parsed.aws_secret_key,
            "gcs_service_account_key": parsed.gcs_service_account_key,
        },
    }

    del parsed.processes
    del parsed.log_file, parsed.log_level, parsed.verbose, parsed.profile_execution_time
    del parsed.aws_profile_name, parsed.aws_access_key, parsed.aws_secret_key, parsed.gcs_service_account_key
    return ctx_args, parsed


def main(parsed: argparse.Namespace):
    try:
        ctx, parsed = split_args(parsed)
        subparser_name = parsed.subparser_name
        del parsed.subparser_name
        with Context(**ctx) as c:
            c.run(run_command, subparser_name, parsed)

    except Exception as err:
        log.error(f"vpt has encountered a runtime error ({err}) and will now exit")
        log.debug(f"Details:\n{err}\n{traceback.format_exc()}")
        sys.exit(1)


def entry_point():
    from vpt.cmd_args import get_postprocess_parser

    main(get_postprocess_parser().parse_args())


if __name__ == "__main__":
    entry_point()
