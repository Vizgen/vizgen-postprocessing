import tempfile
from pathlib import Path
from typing import List

import cv2
import numpy as np
import pytest
import tifffile
from geopandas import GeoDataFrame
from shapely.geometry import MultiPolygon
from tests.base_case import BaseCase
from vpt.sum_signals.main import get_cell_brightness_in_image


class GetCellBrightnessInImageCase(BaseCase):
    img_path = Path(__file__).parent / 'data' / 'image.tif'

    def __init__(self, name: str, image: np.ndarray, boundaries: List,
                 sum_signal: np.ndarray):
        super(GetCellBrightnessInImageCase, self).__init__(name)

        self.image = image
        self.boundaries = boundaries
        self.sum_signal = sum_signal

    def generate_data(self):
        GetCellBrightnessInImageCase.img_path.parent.mkdir(parents=True, exist_ok=True)

        cv2.imwrite(str(GetCellBrightnessInImageCase.img_path), self.image)

    def clean_up_data(self):
        GetCellBrightnessInImageCase.img_path.unlink()


GET_CELL_BRIGHTNESS_IN_IMAGE_CASES = []

image = np.zeros((512, 512))
image[192: 448, 128:256] = 1
image[0:32, 64:128] = 0.7

case = GetCellBrightnessInImageCase(
    'rectangles',
    image,
    [MultiPolygon([([(128, 192), (256, 192), (256, 448), (128, 448)], [])]),
     MultiPolygon([([(64, 0), (64, 32), (128, 32), (128, 0)], [])])],
    sum_signal=np.array([128 * 256, 0.7 * 32 * 64])
)

GET_CELL_BRIGHTNESS_IN_IMAGE_CASES.append(case)


@pytest.mark.parametrize('case', GET_CELL_BRIGHTNESS_IN_IMAGE_CASES, ids=str)
def test_get_cell_brightness_in_image(case: GetCellBrightnessInImageCase) -> None:
    try:
        case.generate_data()

        gdf = GeoDataFrame({
            'ID': np.arange(len(case.boundaries)),
            'EntityID': np.arange(len(case.boundaries)),
            'Geometry': case.boundaries
        })
        res, res_high_pass = get_cell_brightness_in_image(
            str(GetCellBrightnessInImageCase.img_path),
            ((row['EntityID'], row['Geometry']) for _, row in gdf.iterrows()))

        assert np.max(np.abs(res - case.sum_signal) / case.sum_signal) < 0.01
        assert np.max(res_high_pass) >= 0
    finally:
        case.clean_up_data()


def test_1d_poly_does_not_crash():
    image = np.zeros((512, 512))
    image[192: 448, 128:256] = 1
    image[0:32, 64:128] = 0.7

    boundaries = [MultiPolygon([([(128, 192), (256, 192), (256, 192), (128, 192)], [])]),
                  MultiPolygon([([(64, 0), (64, 32), (64, 32), (64, 0)], [])])]

    gdf = GeoDataFrame({'ID': np.arange(2), 'EntityID': np.arange(2), 'Geometry': boundaries})

    with tempfile.TemporaryDirectory() as td:
        img_path = (Path(td) / 'image.tiff').as_posix()
        tifffile.imwrite(img_path, image)
        get_cell_brightness_in_image(
            str(img_path),
            ((row['EntityID'], row['Geometry']) for _, row in gdf.iterrows()))
