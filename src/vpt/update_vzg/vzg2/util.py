import json
import os
import shutil
import tarfile
from datetime import datetime
from typing import Optional

import numpy as np
from vpt_core.io.vzgfs import vzg_open


def extract_vzg2(vzg2_path: str, output_dir: str) -> None:
    with tarfile.open(fileobj=vzg_open(vzg2_path, "rb")) as tar:
        tar.extractall(output_dir)


def read_manifest(root_dir: str) -> dict:
    with open(os.path.join(root_dir, "manifest.json"), "r") as f:
        manifest = json.load(f)
    return manifest


def get_experiment_geometry(manifest: dict) -> tuple:
    tex_width = manifest["mosaic_width_pixels"]
    tex_height = manifest["mosaic_height_pixels"]
    num_z_planes = manifest["planes_count"]
    x_min, y_min, x_max, y_max = manifest["bbox_microns"]

    ax = tex_width / (x_max - x_min)
    bx = -x_min * ax

    ay = tex_height / (y_max - y_min)
    by = -y_min * ay

    transform = np.array([[ax, 0, bx], [0, ay, by], [0, 0, 1]], dtype=np.float32)

    return (tex_width, tex_height), transform, num_z_planes


def update_manifest(manifest, feature_names: list, feature_paths: list) -> None:
    new_manifest_section = list()

    for feature_name, feature_path in zip(feature_names, feature_paths):
        new_manifest_section.append({"name": feature_name, "path": feature_path})

    manifest["features"] = new_manifest_section
    manifest["updated"] = datetime.now().isoformat()


def write_manifest(root_dir: str, manifest: dict):
    with open(os.path.join(root_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f)


def remove_existing_feature_sets(root_dir: str, manifest: Optional[dict] = None) -> None:
    if manifest is None:
        manifest = read_manifest(root_dir)

    for feature_dict in manifest["features"]:
        feature_set_path = os.path.join(root_dir, feature_dict["path"])

        if not os.path.exists(feature_set_path):
            # This condition should never be true, but was added for stability
            continue

        shutil.rmtree(feature_set_path)
