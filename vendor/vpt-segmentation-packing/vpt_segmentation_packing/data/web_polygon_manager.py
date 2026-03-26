"""Module that filters and packs web polygons"""

import math
from enum import Enum

import mapbox_earcut as earcut
import numpy as np

from vpt_segmentation_packing.data.polygon_manager import PolygonManager
from vpt_segmentation_packing.util.convex_hull import build_convex_hull
from vpt_segmentation_packing.util.vector_operations import polygon_area, pseudo_scalar


def size_poly_filter(points: np.ndarray, sizeThreshold: float) -> bool:
    """Checks if polygon big enough to visualize (if polygon smaller - it
    means that segmentation error occurred)

    Compare polygon bbox diagonal with sizeThreshold.
    Args:
        points: (np.array) - polygon points
        sizeThreshold: (float) - diagonal polygon filter threshold in [0, 1]
    Returns:
        (bool) - result if polygon pass filtration
    """
    bbox = (points.min(axis=0), points.max(axis=0))

    deltaX = bbox[1][0] - bbox[0][0]
    deltaY = bbox[1][1] - bbox[0][1]
    return deltaX * deltaX + deltaY * deltaY > sizeThreshold * sizeThreshold


class WebLodLevel(Enum):
    """Enum class of levels of details (lods) type depended on vertex count."""

    LOD0 = 0
    LOD1 = 1
    LOD2 = 2
    COUNT = 3


WebLodsLevel = (WebLodLevel.LOD0, WebLodLevel.LOD1, WebLodLevel.LOD2)


class WebPolygonManager(PolygonManager):
    """Class for handle (filter, pack, save) web polygons"""

    POINTS_NUMBER = (44, 16, 8)

    POINTS_IN_PACK_GROUP = (4, 2)

    COS_45_DEGREE = math.cos(math.pi / 4)
    SIN_45_DEGREE = math.sin(math.pi / 4)

    def __init__(self, zSlice: int, spatialId: str = ""):
        super().__init__(zSlice, spatialId)

        self._polyLinesLods: list[bytearray] = []
        self._polyIndicesLods: list[bytes] = []
        self._tileBelonging = np.zeros((WebLodLevel.COUNT.value, 2), dtype=np.uint32)

        for lodLevel in WebLodsLevel:
            self._polyLinesLods.append(bytearray())

            if lodLevel != WebLodLevel.LOD2:
                self._polyIndicesLods.append(bytes())

        self._polyOnLodExist = np.ones(4, dtype=np.bool_)

    def get_xy(self, lodLevel: int) -> tuple[int, int]:
        return self._tileBelonging[lodLevel][0], self._tileBelonging[lodLevel][1]

    def get_z(self) -> int:
        return self._zSlice

    def get_poly_existence(self, lodLevelValue: int) -> bool:
        return self._polyOnLodExist[lodLevelValue]

    def get_lines(self, lodLevel: int) -> bytearray:
        return self._polyLinesLods[lodLevel]

    def get_indices(self, lodLevel: int) -> bytes:
        return self._polyIndicesLods[lodLevel]

    def points_transform(
        self,
        points: np.ndarray,
        transformMatrix: np.ndarray,
        textureSize: tuple[int, int],
        gridSizeList: list[tuple[int, int]],
    ) -> bool:
        """Transforms polygons points into packed (bytearray) constructions, preliminarily filtered and reduced them
        by lod level.

        Args:
            points: (np.ndarray): 2-dimensial array of polygon points
            transformMatrix: transformation matrix from experiment domain to texture domain.
            textureSize: tuple of original texture width and height.
            gridSizeList:  tuple of grid tiles count for each lod level.
        """
        self._scaling_web(points, transformMatrix)
        points = points.astype(np.int32)
        points = self._thinning_web(points)
        if len(points) < 3:
            return False

        points = self._one_straight_points_reduction(points)
        if len(points) < 3 or not size_poly_filter(points, transformMatrix[0][0] * 3):
            return False

        for lodLevel in WebLodsLevel:
            points = self._vertex_level_reduce(points, self.POINTS_NUMBER[lodLevel.value])
            # upper left tile point
            if lodLevel == WebLodLevel.LOD2:
                self._fill_lod_by_instance(points, transformMatrix, textureSize, gridSizeList[lodLevel.value])
            else:  # Lod0, Lod1
                self._fill_lod_by_geometry(points, textureSize, lodLevel, gridSizeList[lodLevel.value])

        return True

    def _define_tile_belonging(
        self, point: np.ndarray, textureSize: tuple[int, int], gridSize: tuple[int, int], lodLevel: WebLodLevel
    ) -> None:
        xGrid = np.uint32(point[0] / textureSize[0] * gridSize[0])
        yGrid = np.uint32(point[1] / textureSize[1] * gridSize[1])

        self._tileBelonging[lodLevel.value][0] = xGrid
        self._tileBelonging[lodLevel.value][1] = yGrid

    def _define_corner_point(
        self, textureSize: tuple[int, int], gridSize: tuple[int, int], lodLevel: WebLodLevel
    ) -> np.ndarray:
        xGrid, yGrid = self._tileBelonging[lodLevel.value]
        return np.asarray(
            [xGrid * textureSize[0] // gridSize[0], yGrid * textureSize[1] // gridSize[1]], dtype=np.uint32
        )

    @staticmethod
    def _define_base_point(points: np.ndarray) -> np.ndarray:
        """Base point is left upper polygon bbox corner"""
        return points.min(axis=0)

    def _fill_lod_by_geometry(self, points, textureSize, lodLevel: WebLodLevel, gridSize):
        # triangulation
        pointsCount = len(points)
        # triangulation  # pylint: disable=c-extension-no-member
        indices = earcut.triangulate_int32(points, np.array([pointsCount])).tolist()
        indicesLen = len(indices)

        if indicesLen == 0 or (indicesLen > (pointsCount - 2) * 3):  # broken poly by segmentation
            print("Find non triangulated polygon -> make convex hull")
            hullIndices = build_convex_hull(points)
            points = points[hullIndices]
            # triangulation  # pylint: disable=c-extension-no-member
            indices = earcut.triangulate_int32(points, np.array([len(points)])).tolist()
            indicesLen = len(indices)

        for idx in range(indicesLen, (self.POINTS_NUMBER[lodLevel.value] - 2) * 3):
            indices.append(0)
        self._polyIndicesLods[lodLevel.value] = np.asarray(indices, dtype=np.uint8).tobytes()

        # packing
        basePoint = self._define_base_point(points)
        self._define_tile_belonging(basePoint, textureSize, gridSize, lodLevel)
        cornerPoint = self._define_corner_point(textureSize, gridSize, lodLevel)

        self._pack_lines(basePoint, cornerPoint, points, lodLevel)

    def _fill_lod_by_instance(self, points, transformMatrix, textureSize, gridSize):
        centerPoint = points.mean(axis=0)
        self._define_tile_belonging(centerPoint, textureSize, gridSize, WebLodLevel.LOD2)
        cornerPoint = self._define_corner_point(textureSize, gridSize, WebLodLevel.LOD2)

        # define radius
        polygonArea = polygon_area(points[:, 0], points[:, 1])

        shift = centerPoint - cornerPoint
        shift[0] /= textureSize[0]
        shift[1] /= textureSize[1]

        ellipseApproximateParams = self._approximate_by_ellipse(points, polygonArea, centerPoint)

        instanceBtr = self._pack_instance(shift, transformMatrix, gridSize, ellipseApproximateParams)
        self._polyLinesLods[WebLodLevel.LOD2.value].extend(instanceBtr)

    @staticmethod
    def _pack_instance(shift: np.ndarray, transformMatrix, gridSize, ellipseApproximateParams: list) -> bytearray:
        instanceBtr = bytearray()

        centerX = np.uint32(min((shift[0] * gridSize[0]) * (1 << 12), (1 << 12) - 1))
        centerY = np.uint32(min((shift[1] * gridSize[1]) * (1 << 12), (1 << 12) - 1))
        ellipseAMicrons = min(ellipseApproximateParams[0] / transformMatrix[0][0], 16)
        ellipseBMicrons = ellipseApproximateParams[1] / transformMatrix[1][1]
        ellipseRotateAngleType = np.uint32(ellipseApproximateParams[2])

        ellipseScale = np.uint32(min(max(math.ceil(ellipseBMicrons * 6 / ellipseAMicrons - 3), 0), 3))

        packedParams = np.uint32(
            np.uint32((np.uint32(ellipseAMicrons) - 1) << 4) + (ellipseScale << 2) + ellipseRotateAngleType
        )
        firstWord = np.uint32((centerX << 20) + (centerY << 8) + packedParams)

        instanceBtr.extend(firstWord.tobytes())
        return instanceBtr

    @staticmethod
    def _approximate_by_ellipse(points: np.ndarray, polyArea, rotatePoint) -> list:
        points = points - rotatePoint
        bBox = (points.min(0), points.max(0))
        bigDiagonal0 = bBox[1][0] - bBox[0][0]
        bigDiagonal1 = bBox[1][1] - bBox[0][1]

        rotatedPoints = points.copy()
        for point in rotatedPoints:
            newX = point[0] * WebPolygonManager.COS_45_DEGREE - point[1] * WebPolygonManager.SIN_45_DEGREE
            newY = point[1] * WebPolygonManager.COS_45_DEGREE + point[0] * WebPolygonManager.SIN_45_DEGREE

            point[0] = newX
            point[1] = newY

        bBoxRotated = (rotatedPoints.min(0), rotatedPoints.max(0))
        bigDiagonal2 = bBoxRotated[1][0] - bBoxRotated[0][0]
        bigDiagonal3 = bBoxRotated[1][1] - bBoxRotated[0][1]

        approximateParamsList = [[bigDiagonal0, 0], [bigDiagonal1, 2], [bigDiagonal2, 1], [bigDiagonal3, 3]]

        maxDiagonalIdx = 0
        for idx in range(1, len(approximateParamsList)):
            if approximateParamsList[maxDiagonalIdx][0] < approximateParamsList[idx][0]:
                maxDiagonalIdx = idx

        approximateParams = approximateParamsList[maxDiagonalIdx]
        approximateParams[0] /= 2
        ellipseWidth = polyArea / math.pi / approximateParams[0]
        approximateParams.insert(1, ellipseWidth)
        return approximateParams

    def _pack_lines(
        self,
        basePoint: np.ndarray,
        cornerPoint: np.ndarray,
        points: np.ndarray,
        lodLevel: WebLodLevel,
    ):
        packedPolyBtr = bytearray()

        baseShiftPoint = basePoint - cornerPoint
        packedPolyBtr.extend(np.uint32(np.uint32(baseShiftPoint[0] << 16) + baseShiftPoint[1]).tobytes())

        self._pack_deltas(points - basePoint, packedPolyBtr, lodLevel)
        self._polyLinesLods[lodLevel.value].extend(packedPolyBtr)

    def _pack_deltas(self, pointsDeltas, packedPolyBtr, lodLevel):
        if lodLevel == WebLodLevel.LOD1:
            pointsDeltas //= 4

        pointsCount = len(pointsDeltas)
        maxPointsNumber = self.POINTS_NUMBER[lodLevel.value]
        pointsInGroup = self.POINTS_IN_PACK_GROUP[lodLevel.value]
        packGroup = self._get_pack_group_function(lodLevel)

        pointsCounter = 0
        semiGroupSize = pointsCount % pointsInGroup
        if pointsCount // pointsInGroup != 0:
            for pointInd in range(0, pointsCount - semiGroupSize, pointsInGroup):
                packedPolyBtr.extend(packGroup(pointsDeltas, pointInd))
                pointsCounter += pointsInGroup

        if semiGroupSize != 0:
            packedPolyBtr.extend(packGroup(pointsDeltas, pointsCounter, semiGroupSize))
            pointsCounter += pointsInGroup

        # duplicate last point
        lastPointGroup = np.full((pointsInGroup, 2), pointsDeltas[-1])
        for _ in range(pointsCounter, maxPointsNumber, pointsInGroup):
            packedPolyBtr.extend(packGroup(lastPointGroup, 0))

    @staticmethod
    def _pack4_points(deltas, startInd, pointsCount=4) -> bytearray:
        packedBtr = bytearray()
        offsets = np.zeros(4, dtype=np.uint32)

        for pointIdx in range(startInd, startInd + pointsCount):
            deltaX = deltas[pointIdx][0]
            deltaY = deltas[pointIdx][1]
            offsets[pointIdx - startInd] = np.uint32(np.uint32(deltaX << 12) + deltaY)

        for pointIdx in range(startInd + pointsCount, startInd + 4):
            deltaX = deltas[startInd + pointsCount - 1][0]
            deltaY = deltas[startInd + pointsCount - 1][1]
            offsets[pointIdx - startInd] = np.uint32(np.uint32(deltaX << 12) + deltaY)

        packedBtr.extend(np.uint32((offsets[0] << 8) + (offsets[1] >> 16)).tobytes())
        packedBtr.extend(np.uint32((offsets[1] << 16) + (offsets[2] >> 8)).tobytes())
        packedBtr.extend(np.uint32((offsets[2] << 24) + offsets[3]).tobytes())
        return packedBtr

    @staticmethod
    def _pack2_points(deltas, startInd=0, pointsCount=2):
        packedBtr = bytearray()

        offsets = np.zeros(2, dtype=np.uint32)

        for pointIdx in range(startInd, startInd + pointsCount):
            deltaX = deltas[pointIdx][0]
            deltaY = deltas[pointIdx][1]
            offsets[pointIdx - startInd] = np.uint32(np.uint32(deltaX << 8) + deltaY)

        for pointIdx in range(startInd + pointsCount, startInd + 2):
            deltaX = deltas[startInd + pointsCount - 1][0]
            deltaY = deltas[startInd + pointsCount - 1][1]
            offsets[pointIdx - startInd] = np.uint32(np.uint32(deltaX << 8) + deltaY)

        packedBtr.extend(np.uint32((offsets[0] << 16) + offsets[1]).tobytes())
        return packedBtr

    @staticmethod
    def _pack8_points(deltas, startInd=0, pointsCount=8):
        packedBtr = bytearray()
        offsets = np.zeros(8, dtype=np.uint32)

        for pointIdx in range(startInd, startInd + pointsCount):
            deltaX = deltas[pointIdx][0]
            deltaY = deltas[pointIdx][1]

            offsets[pointIdx - startInd] = np.uint32(np.uint32(deltaX << 6) + deltaY)

        for pointIdx in range(startInd + pointsCount, startInd + 8):
            deltaX = deltas[startInd + pointsCount - 1][0]
            deltaY = deltas[startInd + pointsCount - 1][1]
            offsets[pointIdx - startInd] = np.uint32(np.uint32(deltaX << 6) + deltaY)

        first = np.uint32(
            (offsets[0] << 20) + (offsets[1] << 8) + (offsets[2] >> 4)  # 12 bit (x, y)  # 12 bit (x, y)
        )  # 8 bit (6 per x, 2 per y)
        second = np.uint32(
            (offsets[2] << 28)
            + (offsets[3] << 16)  # 4 bit (4 per y)
            + (offsets[4] << 4)  # 12 bit (x, y)
            + (offsets[5] >> 8)  # 12 bit (x, y)
        )  # 4 bit (4 per x)
        third = np.uint32(
            (offsets[5] << 24) + (offsets[6] << 12) + (offsets[7])  # 8 bit (2 per x, 6 per y)  # 12 bit (x, y)
        )  # 12 bit (x, y)

        packedBtr.extend(first.tobytes())
        packedBtr.extend(second.tobytes())
        packedBtr.extend(third.tobytes())
        return packedBtr

    def _get_pack_group_function(self, lodLevel: WebLodLevel):
        return (self._pack4_points, self._pack2_points, self._pack8_points)[lodLevel.value]

    @staticmethod
    def _find_next_concave_index(points: np.ndarray) -> int:
        n = len(points)
        pointA = points[n - 1]
        for pointIdx in range(n):
            pointB = points[pointIdx]
            pointC = points[(pointIdx + 1) % n]

            # check for "bad" (concave) point
            if pseudo_scalar(pointA - pointB, pointC - pointB) > 0:
                return pointIdx

            pointA = pointB

        return -1
