import json
import os
from typing import Dict

from vpt.filesystem.vzgfs import filesystem_path_split, vzg_open
from vpt.prepare_segmentation.constants import OUTPUT_FILE_NAME

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


def save_to_json(output_dict: Dict, output_path: str) -> None:

    fs, path_inside_fs = filesystem_path_split(output_path)

    fs.mkdirs(path_inside_fs, exist_ok=True)

    with vzg_open(fs.sep.join([output_path, OUTPUT_FILE_NAME]), 'w') as f:
        json.dump(output_dict, f, indent=2)
