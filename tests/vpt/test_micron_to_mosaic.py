from pathlib import Path
from typing import List, Optional

import pytest
from vpt_core.io.vzgfs import initialize_filesystem
from vpt_core.utils.base_case import BaseCase

from vpt.utils.input_utils import read_micron_to_mosaic_transform

TEST_DATA_ROOT = (Path(__file__).parent / "data").resolve()


class MicronToMosaicCase(BaseCase):
    def __init__(self, name: str, path: Path, result: Optional[List[List[float]]]):
        super(MicronToMosaicCase, self).__init__(name)
        self.path = path
        self.result = result


MICRON_TO_MOSAIC_CASES = [
    MicronToMosaicCase(
        name="good",
        path=TEST_DATA_ROOT / "micron_to_mosaic_pixel_transform.csv",
        result=[
            [9.259590148925781250e00, 0.000000000000000000e00, -1.254944915771484375e02],
            [0.000000000000000000e00, 9.259541511535644531e00, 1.215537033081054688e02],
            [0.000000000000000000e00, 0.000000000000000000e00, 1.000000000000000000e00],
        ],
    ),
    MicronToMosaicCase(name="bad_element", path=TEST_DATA_ROOT / "bad_element.csv", result=None),
    MicronToMosaicCase(name="bad_shape", path=TEST_DATA_ROOT / "bad_shape.csv", result=None),
]

initialize_filesystem()


@pytest.mark.parametrize("case", MICRON_TO_MOSAIC_CASES, ids=str)
def test_read_micron_to_mosaic_transform(case: MicronToMosaicCase) -> None:
    if case.result is None:
        with pytest.raises(Exception):
            read_micron_to_mosaic_transform(str(case.path))
    else:
        result = read_micron_to_mosaic_transform(str(case.path))

        for row_read, row_true in zip(result, case.result):
            for elem_read, elem_true in zip(row_read, row_true):
                assert abs(elem_read - elem_true) < 1e-16
