from typing import Tuple
import numpy as np

from vpt.update_vzg.polygons.packedpolygon import PackedPolygon, LodLevel


class PackedStarPolygon(PackedPolygon):
    """Class for getting packed star polygon.

    Packing information (B - byte, 1b - bit):
    |1B|3B|20b|12b|20b|12b|12b|12b|..|12b|12b|..
    |k |N | X |dX0| Y |dY0|dX1|dY1|..|dXk|dYk|..
    Here:
        k is the real number point of the polygon.
        N is the number of the polygon.
        X, Y are the coordinates of the first point of the polygon.
        dX0, dY0 is the displacement from the center to the first polygon point.
        dXk, dYk is the displacement from the center to the point k (k > 0).
    """

    LOD_POINTS = [
        [17, 33, 57],
        [8, 16, 32],
        [0, 0, 0]
    ]

    def __init__(self, points, gridSize: Tuple[float, float], lodLevel=LodLevel.Max):
        super().__init__(points)
        self._gridSize = gridSize
        self._lodLevel = lodLevel

    def get_packed_bytes(self, cellId) -> Tuple[int, bytes]:
        """Transfer star polygon into packed block.
        Returns:
             (poly size type index(0, 1, 2), packed block).
        """
        pointsCount = len(self._points)
        packedPolyBtr = bytearray()

        polyType, packedPointCount = self._define_packed_points(pointsCount)
        packedPolyBtr.extend(np.uint32(
            np.uint32(np.uint32(pointsCount - 1) << 24) + np.uint32(cellId)))

        centerPoint = self._points.mean(0)

        firstPointDeltaX = (self._points[0][0] - centerPoint[0]) * self._gridSize[0] * 0.5 + 0.5
        firstPointDeltaY = (self._points[0][1] - centerPoint[1]) * self._gridSize[1] * 0.5 + 0.5

        bitsCenterX = np.uint32(np.uint32(centerPoint[0] *
                                          self.CENTER_POINT_PACK_FACTOR) << 12)
        bitsFirstPointDeltaX = np.uint32(firstPointDeltaX * (1 << 12))
        packedPolyBtr.extend(np.uint32(bitsCenterX + bitsFirstPointDeltaX))

        bitsCenterY = np.uint32(np.uint32(centerPoint[1] *
                                          self.CENTER_POINT_PACK_FACTOR) << 12)
        bitsFirstPointDeltaY = np.uint32(firstPointDeltaY * (1 << 12))
        packedPolyBtr.extend(np.uint32(bitsCenterY + bitsFirstPointDeltaY))

        lastPointsCount = (pointsCount - 1) % 4
        multipled4Points = pointsCount - 1 - lastPointsCount
        for pointInd in range(1, multipled4Points, 4):
            packedPolyBtr.extend(
                self._pack4_points(pointInd, centerPoint, self._gridSize))

        if lastPointsCount != 0:
            packedPolyBtr.extend(self._pack4_points(
                multipled4Points + 1, centerPoint, self._gridSize,
                lastPointsCount))
            multipled4Points += 4

        for _ in range(multipled4Points, packedPointCount - 1, 4):
            packedPolyBtr.extend(np.zeros(3, dtype=np.uint32))

        return polyType, bytes(packedPolyBtr)

    def _define_packed_points(self, pointsCount):
        for i, threshold in enumerate(self.LOD_POINTS[self._lodLevel.value]):
            if pointsCount <= threshold:
                return i, threshold

        return 0, 0

    def get_packed_bytes_middle(self, cellId):
        """Transfer middle-lod star polygon into packed block.
        Returns:
             (poly size type index(0, 1, 2), packed block).
        """
        pointsCount = len(self._points)
        packedPolyBtr = bytearray()

        packedPolyBtr.extend(np.uint32(
            np.uint32(np.uint32(pointsCount - 1) << 24) + np.uint32(cellId)))

        polyType, packedPointCount = self._define_packed_points(pointsCount)
        centerPoint = self._points.mean(0)
        packedPolyBtr.extend(
            np.uint16(self._unsigned_float_to_n_bits(centerPoint[0], 16)))
        packedPolyBtr.extend(
            np.uint16(self._unsigned_float_to_n_bits(centerPoint[1], 16)))

        blocks8Count = 0
        for startPointIdx in range(0, pointsCount, 8):
            pointDelta = pointsCount - startPointIdx
            packSize = 8 if pointDelta > 8 else pointDelta
            self._pack8_points(
                startPointIdx, centerPoint, packedPolyBtr, packSize)
            blocks8Count += 1

        for _ in range(packedPointCount - blocks8Count * 8):
            packedPolyBtr.extend(np.uint16(0))

        return polyType, bytes(packedPolyBtr)

    @staticmethod
    def get_bytes_count(level: LodLevel, packSizeType) -> int:
        """Returns Block bytes count depended on LodLevel and packSizeType.
        Args:
            level: LodLevel.
            packSizeType: index (0, 1, 2) to get points count  in
            LOD_POINTS[LodLevel].
        Returns:
            (int): Block bytes count.
        """
        packSize = PackedStarPolygon.LOD_POINTS[level.value][packSizeType]
        if level == LodLevel.Max:
            return PackedPolygon.BASE_SIZE[level] + \
                   PackedPolygon.BYTE_ON_POINT[level] * (packSize - 1)
        else:  # level == LodLevel.Middle
            return PackedPolygon.BASE_SIZE[level] \
                   + PackedPolygon.BYTE_ON_POINT[level] * packSize

    def _pack8_points(self, startInd, centerPoint, packedPolyBtr,
                      pointsCount=8):
        offsets = np.zeros(8, dtype=np.uint32)
        for pointIdx in range(pointsCount):
            deltaX = (self._points[startInd + pointIdx][0] - centerPoint[0]) * self._gridSize[0] * 0.5 + 0.5
            deltaY = (self._points[startInd + pointIdx][1] - centerPoint[1]) * self._gridSize[1] * 0.5 + 0.5
            offsets[pointIdx] = np.uint32(np.uint32(deltaX * (1 << 8)) << 8) + np.uint32(deltaY * (1 << 8))

        for i in range(4):
            packedPolyBtr.extend(np.uint16(offsets[2 * i + 1]))
            packedPolyBtr.extend(np.uint16(offsets[2 * i]))
