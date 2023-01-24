import numpy as np
from enum import Enum


class LodLevel(Enum):
    """Enum class of levels of details (lods) type depended on vertex count."""
    Max = 0
    Middle = 1
    Min = 2
    Count = 3


class PackedPolygon:
    """Abstract class for getting packed polygons."""
    BASE_SIZE = {
        LodLevel.Max: 12,
        LodLevel.Middle: 8
    }

    BYTE_ON_POINT = {
        LodLevel.Max: 3,
        LodLevel.Middle: 2
    }
    DELTA_PACK_FACTOR = np.uint32(1 << 12)

    CENTER_POINT_PACK_FACTOR = np.uint32(1 << 20)

    def __init__(self, points):
        self._points = points

    @staticmethod
    def _unsigned_float_to_n_bits(float_value, pack_factor):
        return np.uint32(float_value * np.uint32(1 << pack_factor))

    def _pack4_points(self, start_idx, support_point, scale_factor, points_count=4) -> bytearray:
        packed_byte_array = bytearray()
        offsets = np.zeros(4, dtype=np.uint32)

        for point_idx in range(start_idx, start_idx + points_count):
            delta_x = (self._points[point_idx][0] - support_point[0]) * scale_factor[0] * 0.5 + 0.5
            delta_y = (self._points[point_idx][1] - support_point[1]) * scale_factor[1] * 0.5 + 0.5

            delta_x = max(min(1 - 1 / (1 << 12), delta_x), 0)
            delta_y = max(min(1 - 1 / (1 << 12), delta_y), 0)

            offsets[point_idx - start_idx] = \
                np.uint32(np.uint32(delta_x * (1 << 12)) << 12) + np.uint32(delta_y * (1 << 12))

        packed_byte_array.extend(np.uint32((offsets[0] << 8) + (offsets[1] >> 16)))
        packed_byte_array.extend(np.uint32((offsets[1] << 16) + (offsets[2] >> 8)))
        packed_byte_array.extend(np.uint32((offsets[2] << 24) + offsets[3]))
        return packed_byte_array
