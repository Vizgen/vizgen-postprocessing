import logging
import pathlib
import sys

from tqdm import tqdm

_t_id = '/'


class VPTFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.tid = _t_id
        return super().format(record)


vpt_logger = logging.getLogger('vpt')
logger: logging.Logger = vpt_logger
h_stdout = logging.StreamHandler(sys.stdout)
formatter = VPTFormatter('%(asctime)s - %(tid)s - %(levelname)s - %(message)s')
h_stdout.setFormatter(formatter)


def set_logger(user_logger: logging.Logger):
    global logger, vpt_logger
    vpt_logger = logger
    logger = user_logger
    set_verbose(True)


def release_logger():
    global logger, vpt_logger
    logger = vpt_logger


def set_process_name(proc_name: str):
    global _t_id
    _t_id = proc_name


def initialize_logger(fname: str, lvl: int = 1, verbose: bool = False) -> None:
    logger.setLevel(lvl * 10)
    if fname:
        pathlib.Path(fname).parent.mkdir(parents=True, exist_ok=True)
        set_log_file(fname)
    set_verbose(verbose)


def set_log_file(fname: str) -> None:
    fh = logging.FileHandler(filename=fname)
    fh.setFormatter(formatter)
    logger.addHandler(fh)


def set_verbose(v: bool = True) -> None:
    std_in = is_verbose()
    if std_in == v:
        return
    if v:
        logger.addHandler(h_stdout)
    else:
        logger.removeHandler(h_stdout)


def is_verbose() -> bool:
    return h_stdout in logger.handlers


def show_progress(iterable, *args, **kwargs):
    return iterable if not is_verbose() else tqdm(iterable, *args, **kwargs)


def debug(msg, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    logger.info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    logger.error(msg, *args, **kwargs)


def exception(msg, *args, **kwargs):
    logger.error(msg, *args, exc_info=True, **kwargs)


def critical(msg, *args, **kwargs):
    logger.critical(msg, *args, **kwargs)
