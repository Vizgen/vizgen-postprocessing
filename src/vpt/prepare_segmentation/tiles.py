from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class TileInfo:
    top_left_x: int
    top_left_y: int
    size: int


def make_tiles(image_width: int, image_height: int, tile_size: int, tile_overlap: int) -> List[TileInfo]:
    window_size = tile_size + 2 * tile_overlap
    window_overlap = tile_overlap

    def one_dim_cut(start, end):
        points = [start]
        while points[-1] + 2 * window_size - window_overlap <= end:
            points.append(points[-1] + window_size - window_overlap)
        if points[-1] + window_size < end:
            points.append(end - window_size)
        return points

    x_points = one_dim_cut(0, image_width)
    y_points = one_dim_cut(0, image_height)
    return [TileInfo(x, y, window_size) for y in y_points for x in x_points]
