import os
import tempfile
from abc import abstractmethod, ABC
from datetime import datetime
from pathlib import Path

from vpt.filesystem import filesystem_path_split


class TempDir(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def get_temp_path(self) -> str:
        pass

    @abstractmethod
    def clear_dir(self):
        pass

    def get_sep(self) -> str:
        return os.path.sep

    def __str__(self):
        return ""

    @abstractmethod
    def create_dir(self, name: str):
        pass


class LocalTempDir(TempDir):
    def __init__(self):
        super(LocalTempDir, self).__init__()
        self.td = tempfile.TemporaryDirectory()

    def get_temp_path(self) -> str:
        if not self.td._finalizer.alive:
            self.td = tempfile.TemporaryDirectory()
        return Path(self.td.name).as_posix()

    def clear_dir(self):
        self.td.cleanup()

    def __str__(self):
        return "local"

    def create_dir(self, name: str):
        os.mkdir(Path(self.td.name) / name)


class CloudTempDir(TempDir):
    def __init__(self, dir_path: str):
        super(CloudTempDir, self).__init__()
        self.path = dir_path + datetime.now().strftime('%Y-%m-%dT%H:%M:%S:%f')
        try:
            self.fs, _ = filesystem_path_split(self.path)
        except ValueError:
            self.fs = None

    def get_temp_path(self) -> str:
        return self.path

    def clear_dir(self):
        try:
            self.fs.rm(self.path, recursive=True)
        except Exception:
            pass

    def get_sep(self) -> str:
        return self.fs.sep

    def __str__(self):
        return str(self.fs.protocol) if self.fs else self.path

    def create_dir(self, name: str):
        pass
