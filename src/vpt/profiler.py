import cProfile
import marshal
import pstats
from pathlib import Path
from typing import Optional

from vpt import log
from vpt.filesystem import vzg_open

main_profiler = None
all_stat = None
profiler_output = None


def initialize_profiler(profile_file: Optional[str]):
    global main_profiler, profiler_output
    if profile_file:
        main_profiler = cProfile.Profile()
        profiler_output = profile_file


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
        with vzg_open(profiler_output, 'wb') as f:
            marshal.dump(stats.stats, f)


def append_with_file(fname: str, remove: bool = True):
    if Path(fname).exists():
        append_stat(fname)
        if remove:
            Path(fname).unlink(missing_ok=True)
    else:
        log.warning(f"appending profiling stats failed: {fname} not found")
