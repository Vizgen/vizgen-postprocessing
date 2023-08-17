from typing import List, Tuple

import numpy as np
from vpt_core import log

from vpt.update_vzg.byte_utils import extend_with_u32, extend_with_f32
from vpt.update_vzg.polygons.packedpolygon import PackedPolygon
from vpt.update_vzg.polygons.polystructers import IndexedPolygon


class PackedFanPolygon(PackedPolygon):
    """Class for getting packed fan polygon.

    Packing information (B - byte, 1b - bit):
    | 4B  |  8B | 36 points - 108B |12fans-12B|points count + 2*polycount  |
    |1B|3B|4B|4B|12b|12b|..|12b|12b|1B |..|1B |  1b  |  7b |..|  1b  |  7b |
    |n |N |X |Y |dX1|dY1|..|dXk|dYk|n0 |..|n11|flag_0|idx_0|..|flag_k|idx_k|
    Here:
        n is the number of the cell size type (0: 25.6, 1: 51.2, 2: 71.8)
        N is the number of the polygon
        X, Y are the coordinates of the first point of the polygon
        dXk, dYK is the offset from the point X, Y to a point k;
        nl is the number of points in fan number l;
        flag_k is used when rendering the polygon contour
        idx_k is the index of the point of the fan number k
    """

    Golden_Size = 25.6

    Points_Count = (37, 17, 9)

    Fans_Count = (12, 12, 4)

    Bytes_Count = (196, 120, 64)

    Indices_Count = (64, 48, 16)

    def __init__(self, origins: list, lodLevel):
        super().__init__(origins)
        self._lodLevel = lodLevel

    @staticmethod
    def define_cell_size_factor(cellSize) -> Tuple[int, float]:
        """Defines cell boundary size and cell size type.
        Returns:
             tuple(cell size type, cell boundary size).
        """
        for i in range(3):
            size = PackedFanPolygon.Golden_Size * (i + 1)
            if cellSize < size:
                return i, size

        return 2, PackedFanPolygon.Golden_Size * 3

    def get_packed_bytes(self, polyList: List[IndexedPolygon], cellSize, cellId, expBbox) -> bytes:
        """Transfer polygons (points and indices) into packed block.
        Args:
            polyList: List of IndexedPolygon.
            cellSize: original cell size (diagonal of bbox).
            cellId.
            expBbox: width and height of experiment in microns.
        Returns:
             (bytes): packed block.
        """
        packedPolyBtr = bytearray()

        sizeFactor, sizeNorm = self.define_cell_size_factor(cellSize)
        extend_with_u32(packedPolyBtr, np.uint32(np.uint32(sizeFactor) << 24) + np.uint32(cellId))

        p0 = self._points[0]
        extend_with_f32(packedPolyBtr, p0[0])
        extend_with_f32(packedPolyBtr, p0[1])

        # pack deltas
        normScale = (expBbox[0] / sizeNorm, expBbox[1] / sizeNorm)
        self._pack_deltas(packedPolyBtr, normScale)

        # pack poly count
        self._pack_poly_count(polyList, packedPolyBtr)

        # pack indices
        self._pack_indices(polyList, packedPolyBtr)

        if len(packedPolyBtr) != self.Bytes_Count[self._lodLevel.value]:
            log.warning("Packing error: wrong byte count", len(packedPolyBtr), self._lodLevel)
            return bytes()

        return bytes(packedPolyBtr)

    def _pack_indices(self, polyList: List[IndexedPolygon], packedPolyBtr):
        bytePacked = 0
        maxIndex = self.Indices_Count[self._lodLevel.value]
        indices = np.zeros(maxIndex, dtype=np.uint8)
        idx = 0
        for poly in polyList:  # type: IndexedPolygon
            polyIdx = poly.polyIndices
            includeIdx = poly.includeIndices
            if poly.type == "fan" and poly.ind != 0:
                shift = len(poly.polyIndices) - poly.ind
                polyIdx = polyIdx[-shift:] + polyIdx[:-shift]
                includeIdx = includeIdx[-shift:] + includeIdx[:-shift]

            for i, pIdx in enumerate(polyIdx):
                indices[idx] = np.uint8(np.uint8(includeIdx[i]) << 7) + np.uint8(pIdx)
                idx += 1

        for i in range(0, maxIndex // 4, 1):
            packedPolyBtr.extend(
                np.uint32(indices[i * 4] << 24)
                + np.uint32(indices[i * 4 + 1] << 16)
                + np.uint32(indices[i * 4 + 2] << 8)
                + np.uint32(indices[i * 4 + 3])
            )
            bytePacked += 4

    @staticmethod
    def _pack_poly_count(polyList: List[IndexedPolygon], packedPolyBtr):
        fansCount = np.zeros(12, dtype=np.uint8)
        for i, poly in enumerate(polyList):
            fansCount[i] = np.uint8(len(poly.polyIndices))

        for i in range(3):
            packedPolyBtr.extend(
                np.uint32(fansCount[i * 4] << 24)
                + np.uint32(fansCount[i * 4 + 1] << 16)
                + np.uint32(fansCount[i * 4 + 2] << 8)
                + np.uint32(fansCount[i * 4 + 3])
            )

    def _pack_deltas(self, packedPolyBtr, normScale):
        maxPoint = self.Points_Count[self._lodLevel.value]
        pointsCount = len(self._points)

        lastPointsCount = (pointsCount - 1) % 4
        multipled4Points = pointsCount - 1 - lastPointsCount
        for pointInd in range(1, multipled4Points, 4):
            packedPolyBtr.extend(self._pack4_points(pointInd, self._points[0], normScale))

        if lastPointsCount != 0:
            packedPolyBtr.extend(self._pack4_points(multipled4Points + 1, self._points[0], normScale, lastPointsCount))
            multipled4Points += 4

        for _ in range(multipled4Points, maxPoint - 1, 4):
            packedPolyBtr.extend(np.zeros(3, dtype=np.uint32))
