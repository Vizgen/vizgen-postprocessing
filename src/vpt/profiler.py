import cProfile
import marshal
import pstats
from pathlib import Path
from typing import Optional

from vpt_core import log
from vpt_core.io.vzgfs import io_with_retries

main_profiler: Optional[cProfile.Profile] = None
all_stat: Optional[pstats.Stats] = None
profiler_output: Optional[str] = None


def initialize_profiler(profile_file: Optional[str]):
    global main_profiler, profiler_output
    if profile_file:
        main_profiler = cProfile.Profile()
        profiler_output = profile_file
    else:
        main_profiler = None
        profiler_output = None


def append_stat(statistic_container):
    global all_stat
    if all_stat is None:
        all_stat = pstats.Stats(statistic_container)
    else:
        all_stat.add(statistic_container)


def enable():
    if main_profiler:
        main_profiler.enable()


def disable():
    if main_profiler:
        main_profiler.disable()


def export_data():
    global all_stat, main_profiler
    if main_profiler:
        stats = pstats.Stats(main_profiler)
        if all_stat:
            stats.add(all_stat)
        io_with_retries(profiler_output, "wb", lambda f: marshal.dump(stats.stats, f))


def append_with_file(fname: str, remove: bool = True):
    if Path(fname).exists():
        append_stat(fname)
        if remove:
            Path(fname).unlink(missing_ok=True)
    else:
        log.warning(f"appending profiling stats failed: {fname} not found")
