from typing import List

from vpt.filesystem.vzgfs import filesystem_path_split


def validate_does_not_exist(path: str):
    fs, path_inside_fs = filesystem_path_split(path)
    if fs.exists(path_inside_fs):
        raise ValueError(f'Object already exists: {path}')


def validate_exists(path: str):
    fs, path_inside_fs = filesystem_path_split(path)
    if not fs.exists(path_inside_fs):
        from pathlib import Path
        raise ValueError(f'Object does not exist: {path} {str(Path(path).absolute())}')


def validate_directory_empty(path: str):
    fs, path_inside_fs = filesystem_path_split(path)

    if fs.exists(path_inside_fs) and len(fs.listdir(path_inside_fs, detail=False)) > 0:
        raise ValueError(f'Directory is not empty {path}')


def validate_micron_to_mosaic_transform(transform: List[List[float]]):
    if len(transform) != 3 or not all(map(lambda row: len(row) == 3, transform)):
        raise ValueError('Micron to mosaic transform should be a 3x3 matrix')
