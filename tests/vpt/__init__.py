import os
from pathlib import Path

from vpt import IS_VPT_EXPERIMENTAL_VAR

TEST_DATA_ROOT = (Path(__file__).parent / "data").resolve()
IMAGES_ROOT = TEST_DATA_ROOT / "input_images"
IMAGES_ROOT_MOCK = TEST_DATA_ROOT / "input_images_wide"
OUTPUT_FOLDER = TEST_DATA_ROOT / "output"

os.environ[IS_VPT_EXPERIMENTAL_VAR] = "true"
