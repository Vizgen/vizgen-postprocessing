import json
import math
import os
from enum import Enum
from pathlib import Path
from typing import Dict, List, Tuple

GRID_HEIGHT = 16

GRID_WIDTH = 16

SCALE_X = 16.0

SCALE_Y = 16.0

PACK_FACTOR = 2**24


def grid_size_calculate(textureSize, transformationMatrix) -> Tuple[int, int]:
    """Calculate voxel grid count based on experiment size.
    400 microns - is maximum that voxel side could be for proper
    visualization.
    """
    expWidth = textureSize[0] / transformationMatrix[0][0]
    expHeight = textureSize[1] / transformationMatrix[1][1]

    return math.ceil(expWidth / 400), math.ceil(expHeight / 400)


def load_texture_coords(datasetPath: str) -> List:
    with open(os.path.join(datasetPath, "pictures", "manifest.json"), "r") as read_file:
        picture_manifest_json = json.load(read_file)
    return [picture_manifest_json["mosaic_width_pixels"], picture_manifest_json["mosaic_height_pixels"]]


def load_images_manifest(datasetPath: str) -> Dict:
    with open(os.path.join(datasetPath, "pictures", "manifest.json"), "r") as read_file:
        picture_manifest_json = json.load(read_file)
    return picture_manifest_json


def load_texture_matrix(raw_dataset_path: str) -> List:
    import csv

    matrix = []
    with open(
        os.path.join(raw_dataset_path, "pictures", "micron_to_mosaic_pixel_transform.csv"), newline="\n"
    ) as csvfile:
        matrix_file = csv.reader(csvfile, delimiter=" ", quotechar="|")

        for row in matrix_file:
            matrix_row = []
            for column in row:
                matrix_row.append(float(column))
            matrix.append(matrix_row)

    return matrix


class FileType(Enum):
    Experiment = 0
    Dataset = 1


def write_file(exp_path: str, buffer, file_name, relative_file_path=""):
    file_path = os.path.join(exp_path, relative_file_path)

    Path(file_path).mkdir(parents=True, exist_ok=True)
    with open(os.path.join(file_path, file_name), "bw") as file:
        file.write(buffer)


def write_json_file(analysisResult, exp_path: str, output_filename):
    Path(exp_path).mkdir(parents=True, exist_ok=True)
    with open(os.path.join(exp_path, output_filename), "w") as f:
        json.dump(analysisResult, f, indent=4)


def extend_btr_by_fixed_str(btr: bytearray, string: str, max_bytes_count: int):
    name_len = len(string)
    btr.extend(str.encode(string))
    delta = max_bytes_count - name_len
    btr.extend(bytearray(delta))
