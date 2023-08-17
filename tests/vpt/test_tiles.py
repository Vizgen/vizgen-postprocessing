from typing import List

import pytest
from vpt_core.utils.base_case import BaseCase

from vpt.prepare_segmentation.tiles import TileInfo, make_tiles


class MakeTilesCase(BaseCase):
    def __init__(
        self, name: str, image_width: int, image_height: int, tile_size: int, tile_overlap: int, result: List[TileInfo]
    ):
        super(MakeTilesCase, self).__init__(name)

        self.image_width = image_width
        self.image_height = image_height
        self.tile_size = tile_size
        self.tile_overlap = tile_overlap

        self.result = result


MAKE_TILES_CASES = [
    MakeTilesCase(
        name="even_fit",
        image_width=4096,
        image_height=2560,
        tile_size=512,
        tile_overlap=256,
        result=[
            TileInfo(0, 0, 1024),
            TileInfo(768, 0, 1024),
            TileInfo(1536, 0, 1024),
            TileInfo(2304, 0, 1024),
            TileInfo(3072, 0, 1024),
            TileInfo(0, 768, 1024),
            TileInfo(768, 768, 1024),
            TileInfo(1536, 768, 1024),
            TileInfo(2304, 768, 1024),
            TileInfo(3072, 768, 1024),
            TileInfo(0, 1536, 1024),
            TileInfo(768, 1536, 1024),
            TileInfo(1536, 1536, 1024),
            TileInfo(2304, 1536, 1024),
            TileInfo(3072, 1536, 1024),
        ],
    ),
    MakeTilesCase(
        name="uneven_x",
        image_width=500,
        image_height=500,
        tile_size=200,
        tile_overlap=25,
        result=[
            TileInfo(0, 0, 250),
            TileInfo(225, 0, 250),
            TileInfo(250, 0, 250),
            TileInfo(0, 225, 250),
            TileInfo(225, 225, 250),
            TileInfo(250, 225, 250),
            TileInfo(0, 250, 250),
            TileInfo(225, 250, 250),
            TileInfo(250, 250, 250),
        ],
    ),
    MakeTilesCase(
        name="uneven_y",
        image_width=300,
        image_height=600,
        tile_size=250,
        tile_overlap=25,
        result=[TileInfo(0, 0, 300), TileInfo(0, 275, 300), TileInfo(0, 300, 300)],
    ),
]


@pytest.mark.parametrize("case", MAKE_TILES_CASES, ids=str)
def test_make_tiles(case: MakeTilesCase) -> None:
    result = make_tiles(case.image_width, case.image_height, case.tile_size, case.tile_overlap)
    assert result == case.result
