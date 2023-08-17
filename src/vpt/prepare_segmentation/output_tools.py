import json
import os
from typing import Dict

from vpt_core.io.vzgfs import filesystem_path_split, io_with_retries

from vpt.prepare_segmentation.constants import OUTPUT_FILE_NAME

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"


def save_to_json(output_dict: Dict, output_path: str) -> None:
    fs, path_inside_fs = filesystem_path_split(output_path)

    fs.mkdirs(path_inside_fs, exist_ok=True)

    io_with_retries(
        uri=fs.sep.join([output_path, OUTPUT_FILE_NAME]),
        mode="w",
        callback=lambda f: json.dump(output_dict, f, indent=2),
    )
