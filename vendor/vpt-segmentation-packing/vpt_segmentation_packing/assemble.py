import json
import math
import os
import tarfile


def _make_file_list(inputDir: str) -> list[tuple[str, str]]:
    flist = []

    for gen_dir, subdirs, files in os.walk(inputDir):
        for name in files:
            rel_dir = os.path.relpath(gen_dir, inputDir)
            rel_file = name if rel_dir == "." else os.path.join(rel_dir, name)
            full_path = os.path.join(gen_dir, name)

            if rel_file == "offset_table.json":
                continue

            flist.append((full_path, rel_file))

    return flist


def _make_offset_table(fileList: list[tuple[str, str]]) -> dict:
    offsetTable = {}
    blockSize = 512
    offset = blockSize

    for absPath, relPath in fileList:
        size = os.path.getsize(absPath)
        offsetTable[relPath.replace(os.sep, "/")] = {"offset": offset, "size": size}
        offset += blockSize * math.ceil(size / blockSize) + blockSize

    return offsetTable


def _pack_into_tar(offsetsTablePath: str, fileList: list[tuple[str, str]], outputPath: str) -> None:
    with tarfile.open(outputPath, "w", format=tarfile.GNU_FORMAT) as tar:
        tar.add(offsetsTablePath, "offset_table.json", recursive=False)
        for full, rel in fileList:
            tar.add(full, rel, recursive=False)


def assemble_vzg2(inputDir: str, outputPath: str) -> None:
    """
    Assembles the vzg2 file from the vzg2 structured directory
    """
    fileList = _make_file_list(inputDir)
    offsetTable = _make_offset_table(fileList)

    offsetTablePath = os.path.join(inputDir, "offset_table.json")

    with open(offsetTablePath, "w") as f:
        json.dump(offsetTable, f)

    _pack_into_tar(offsetTablePath, fileList, outputPath)
