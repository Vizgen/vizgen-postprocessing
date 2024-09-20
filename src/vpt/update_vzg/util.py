import os.path
import shutil
from contextlib import contextmanager
from datetime import datetime


@contextmanager
def clean_up_on_exit(temp_dir: str):
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def create_workdir(parent_dir: str) -> str:
    unique_folder_name = f"vzg2_{datetime.now().strftime('%Y-%m-%dT%H_%M_%S_%f')}"
    workdir = os.path.join(parent_dir, unique_folder_name)
    os.makedirs(workdir, exist_ok=True)
    return workdir
