import math
from typing import List, Tuple

import numpy as np

from vpt.update_vzg.polygons.packedfanpolygon import PackedFanPolygon
from vpt.update_vzg.polygons.packedpolygon import LodLevel
from vpt.update_vzg.polygons.packedstarpolygon import PackedStarPolygon
from vpt.update_vzg.polygons.poly_partition import PolyPartition
from vpt.update_vzg.polygons.polystructers import IndexedPolygon
from vpt.update_vzg.polygons.vector_operations import clockwise_traverse, pseudo_scalar


def l2_dist_sqr(deltaX, deltaY):
    """
    Returns:
         L2 squared norm of 2 dimensions.
    """
    return deltaX * deltaX + deltaY * deltaY


class PolygonSet:
    """Class for managing, filtering (vertices), partition, creating lods of 1
    polygon."""

    BIT_FACTOR = 1 << 20

    Info_Message = "Cell with id {0} on Z-slice {1} "

    def __init__(self, zSlice: int, xCenter, yCenter, spatial_id: str = "", cellId=0):
        self._spatialId = spatial_id
        self._cellId = cellId
        self._zSlice = zSlice
        self._xCenter = xCenter
        self._yCenter = yCenter
        self._packedPolygons: List = []

    def get_center(self):
        """Get cell center.
        Returns:
             (cell center x, cell center y, z slIce).
        """
        return self._xCenter, self._yCenter, self._zSlice

    def get_spatial_id(self):
        """Get cell name (spatial id).
        Returns:
             spatial id.
        """
        return self._spatialId

    def get_cell_id(self):
        """Get cell id.
        Returns:
             cell id.
        """
        return self._cellId

    def set_cell_id(self, cellId: int):
        """Sets cell id: to field cellId and to all packed blocks."""
        self._cellId = cellId
        for i in range(len(self._packedPolygons)):
            if len(self._packedPolygons[i][1]) == 0:
                continue

            packedPolygons = bytearray(self._packedPolygons[i][1])
            firstInt = np.uint32(
                int.from_bytes(self._packedPolygons[i][1][0:4], byteorder="little", signed=False)
            ) | np.uint32(cellId)

            firstIntBytes = bytearray()
            firstIntBytes.extend(firstInt.tobytes())

            for byteIdx in range(4):
                packedPolygons[byteIdx] = firstIntBytes[byteIdx]

            self._packedPolygons[i] = (self._packedPolygons[i][0], bytes(packedPolygons))

    def _print_message(self, cause: str, zSlice: int):
        print((self.Info_Message + cause).format(self._cellId, zSlice))

    def points_transform(
        self,
        points: np.ndarray,
        transformMatrix: List,  # text_coord_matrix
        textureSize: Tuple[float, float],
        gridSize: Tuple[float, float],
        expBbox: tuple,
    ) -> bool:
        """
        Runs conveyor of filtering, partition, packing and creating lods.
        Result of this function is list of packed block for each lod level
        (self._packedPolygons).

        Args:
            points: (np.ndarray): 2-dimensial array of polygon points
            transformMatrix: transformation matrix from experiment domain
            to texture domain.
            textureSize: tuple of original texture width and height.
            gridSize: tuple of grid voxels count.
            expBbox: width and height of experiment in microns.
        Returns:
            True - if transformation is succeeded, False - if not.
        """
        points = points.astype("float32")

        bbox = np.max(points, axis=0) - np.min(points, axis=0)
        cellSize = math.sqrt(bbox[0] * bbox[0] + bbox[1] * bbox[1])
        _, cellNormSize = PackedFanPolygon.define_cell_size_factor(cellSize)
        normScale = (expBbox[0] / cellNormSize, expBbox[1] / cellNormSize)

        self._scaling(points, textureSize, transformMatrix)
        result, points = self._poly_filter(points, 57)

        if not result:
            return False

        if clockwise_traverse(points):
            points = points[::-1]

        if not all(
            [
                1 > ((p[0] - points[0][0]) * normScale[0] * 0.5 + 0.5) > 0
                or 1 > ((p[1] - points[0][1]) * normScale[1] * 0.5 + 0.5) > 0
                for p in points[1:]
            ]
        ):
            return False

        if self._poly_star_check(points.copy(), gridSize, expBbox, cellSize, normScale):
            return True

        if len(points) > 37:
            points = self._vertex_level_reduce(points, 37)

        if self._poly_star_check(points.copy(), gridSize, expBbox, cellSize, normScale):
            return True

        # Polygon is fan polygon
        polys: List[IndexedPolygon] = []
        result, points = self._fan_processing(points, polys, normScale)
        if not result:
            return False

        self._make_fan_packed_lods(points, polys, expBbox, cellSize, normScale)
        return True

    def _poly_filter(self, points, maxPoints) -> Tuple[bool, np.ndarray]:
        points = self._thinning(points)
        if len(points) <= 2:
            return False, np.array([])

        if len(points) > maxPoints:
            points = self._vertex_level_reduce(points, maxPoints)

        return True, points

    def _fan_processing(self, points, out: List, normScale):
        pointsMicronDelta = self._points_pack_fan_reduction(points, normScale)
        uniquePointsDelta = np.unique(pointsMicronDelta, return_index=True, axis=0)[1]
        uniquePointsDelta.sort(0)
        pointsMicronDelta = pointsMicronDelta[uniquePointsDelta]
        points = points[uniquePointsDelta]
        if len(points) < 3:
            return False, None

        try:
            polyPartition = PolyPartition(pointsMicronDelta)
            polyPartition.run_partition(out)
        except Exception:
            out.clear()
            return False, None

        if len(out) > 12:
            out.sort(key=lambda x: len(x.polyIndices), reverse=True)
            for _ in range(12, len(out)):
                out.pop()

        return True, points

    def _poly_star_check(self, points, gridSize, expBbox, cellSize, normScale):
        pointsMicronDelta = self._points_pack_star_reduction(points, gridSize)
        uniquePointsDelta = np.unique(pointsMicronDelta, return_index=True, axis=0)[1]
        uniquePointsDelta.sort(0)
        points = points[uniquePointsDelta]
        if len(points) < 3:
            return False

        pointsMicronDelta = self._points_pack_star_reduction(points, gridSize)

        if self._define_star_polygon(pointsMicronDelta):
            self._make_star_packed_lods(points, expBbox, cellSize, normScale, gridSize)
            return True

        return False

    def _make_star_packed_lods(self, points, expBbox, cellSize, normScale, gridSize):
        self._packedPolygons.append(PackedStarPolygon(points, gridSize).get_packed_bytes(self._cellId))

        # middle level
        if len(points) > 32:
            points = self._vertex_level_reduce(points, 32)

        self._packedPolygons.append(
            PackedStarPolygon(points, gridSize, LodLevel.Middle).get_packed_bytes_middle(self._cellId)
        )

        # Min level
        self._fan_packed_lod(points, LodLevel.Min, 9, expBbox, cellSize, normScale)

    def _make_fan_packed_lods(self, points, polys, expBbox, cellSize, normScale):
        fanPoly = PackedFanPolygon(points, LodLevel.Max)
        self._packedPolygons.append((3, fanPoly.get_packed_bytes(polys, cellSize, self._cellId, expBbox)))

        self._fan_packed_lod(points, LodLevel.Middle, 17, expBbox, cellSize, normScale)

        self._fan_packed_lod(points, LodLevel.Min, 9, expBbox, cellSize, normScale)

    def _fan_packed_lod(self, points, lodLevel, filterCount: int, expBbox, cellSize, normScale, polyType=3):
        points = self._vertex_level_reduce(points, filterCount)
        polys: List[IndexedPolygon] = []
        result, points = self._fan_processing(points, polys, normScale)

        if not result:
            self._packedPolygons.append((-1, bytes()))
        else:
            fanPoly = PackedFanPolygon(points, lodLevel)
            self._packedPolygons.append((polyType, fanPoly.get_packed_bytes(polys, cellSize, self._cellId, expBbox)))

    @staticmethod
    def _points_pack_fan_reduction(points, normScale) -> np.ndarray:
        p0 = points[0]
        packFactor12 = 1 << 12
        pointsMicronDelta = np.zeros((len(points), 2), dtype=np.int32)
        pointsMicronDelta[0][0] = packFactor12 / 2
        pointsMicronDelta[0][1] = packFactor12 / 2

        for pIdx in range(1, len(points)):
            delta = points[pIdx] - p0
            xDeltaClamped = max(min(1, delta[0] * normScale[0]), -1)
            xDelta = np.uint32((0.5 * xDeltaClamped + 0.5) * packFactor12)

            yDeltaClamped = max(min(1, delta[1] * normScale[1]), -1)
            yDelta = np.uint32((0.5 * yDeltaClamped + 0.5) * packFactor12)

            pointsMicronDelta[pIdx][0] = xDelta
            pointsMicronDelta[pIdx][1] = yDelta

        return pointsMicronDelta

    @staticmethod
    def _points_pack_star_reduction(points, gridSize) -> np.ndarray:
        center = np.asarray(points.mean(0))
        packFactor12 = 1 << 12
        pointsMicronDelta = np.zeros((len(points), 2), dtype=np.float32)

        for pIdx in range(0, len(points)):
            delta = points[pIdx] - center

            xDelta = np.uint32((0.5 * delta[0] * gridSize[0] + 0.5) * packFactor12)
            yDelta = np.uint32((0.5 * delta[1] * gridSize[1] + 0.5) * packFactor12)

            pointsMicronDelta[pIdx][0] = xDelta
            pointsMicronDelta[pIdx][1] = yDelta

        return pointsMicronDelta

    @staticmethod
    def _scaling(points, textureSize, transformMatrix):
        textureWidth, textureHeight = textureSize

        for point in points:
            x_texture = point[0] * transformMatrix[0][0] + transformMatrix[0][2]
            y_texture = point[1] * transformMatrix[1][1] + transformMatrix[1][2]

            x_world = x_texture / textureWidth
            y_world = 1.0 - y_texture / textureHeight

            point[0] = np.float32(x_world)
            point[1] = np.float32(y_world)

    def _thinning(self, points: np.ndarray):
        bit_factor = self.BIT_FACTOR
        x_start_number = int(points[0][0] * bit_factor)
        y_start_number = int(points[0][1] * bit_factor)
        x_prev_number, y_prev_number = x_start_number, y_start_number

        thinned_bool_filter_arr = [True]

        iter_coords = iter(points)
        next(iter_coords)

        for coords in iter_coords:
            x_curr_number = int(coords[0] * bit_factor)
            y_curr_number = int(coords[1] * bit_factor)

            thinned_bool_filter_arr.append(not (x_curr_number == x_prev_number and y_curr_number == y_prev_number))

            x_prev_number = x_curr_number
            y_prev_number = y_curr_number

        # last point
        x_curr_number = x_start_number
        y_curr_number = y_start_number
        thinned_bool_filter_arr[0] = not (x_curr_number == x_prev_number and y_curr_number == y_prev_number)

        return points[thinned_bool_filter_arr]

    def get_packed_bytes(self, lodLevel=LodLevel.Max) -> Tuple[int, bytes]:
        """Returns packed lod level block.

        Returns:
            (PolyType, packed block), where PolyType is int number:
                -1: packing failed.
                0, 1, 2: three types of star polygon depended on points count.
                3: fan polygon.
        """
        return self._packedPolygons[lodLevel.value]

    @staticmethod
    def _find_next_not_reduced_vertex(trueVerticesList: List[bool], ind: int):
        n = len(trueVerticesList)
        while ind < n and not trueVerticesList[ind]:
            ind += 1

        return ind

    def _vertex_level_reduce(self, points, pointsThreshold) -> np.ndarray:
        primary_vertices_count = vertices_count = len(points)
        coords = points.copy()
        true_vertices_l = [True] * vertices_count  # not reduced
        while vertices_count > pointsThreshold:
            first_not_reduced_ind: int = self._find_next_not_reduced_vertex(true_vertices_l, 0)
            second_not_reduced_ind: int = self._find_next_not_reduced_vertex(true_vertices_l, first_not_reduced_ind + 1)
            dist_first_v, dist_second_v = first_not_reduced_ind, second_not_reduced_ind
            min_dist_sqr = 1000

            while second_not_reduced_ind < primary_vertices_count:
                dist = l2_dist_sqr(
                    coords[first_not_reduced_ind][0] - coords[second_not_reduced_ind][0],
                    coords[first_not_reduced_ind][1] - coords[second_not_reduced_ind][1],
                )
                if dist < min_dist_sqr:
                    min_dist_sqr = dist
                    dist_first_v, dist_second_v = first_not_reduced_ind, second_not_reduced_ind

                first_not_reduced_ind = second_not_reduced_ind
                second_not_reduced_ind = self._find_next_not_reduced_vertex(true_vertices_l, first_not_reduced_ind + 1)

            second_not_reduced_ind = self._find_next_not_reduced_vertex(true_vertices_l, 0)

            dist = l2_dist_sqr(
                coords[first_not_reduced_ind][0] - coords[second_not_reduced_ind][0],
                coords[first_not_reduced_ind][1] - coords[second_not_reduced_ind][1],
            )
            if dist < min_dist_sqr:
                dist_first_v, dist_second_v = first_not_reduced_ind, second_not_reduced_ind

            true_vertices_l[dist_first_v] = False
            coords[dist_second_v][0] = (coords[dist_first_v][0] + coords[dist_second_v][0]) / 2
            coords[dist_second_v][1] = (coords[dist_first_v][1] + coords[dist_second_v][1]) / 2
            vertices_count -= 1

        return coords[true_vertices_l]

    @staticmethod
    def _define_star_polygon(points) -> bool:
        """Determines if polygon set by points, is star polygon.
        Points should be in clockwise order."""

        packFactor12 = 1 << 12

        center = np.asarray((packFactor12 / 2, packFactor12 / 2), dtype=np.float32)
        coordsCount = len(points)

        for barcodeIdx in range(coordsCount - 1):
            vectorA = points[barcodeIdx] - center
            vectorB = points[barcodeIdx + 1] - center
            if pseudo_scalar(vectorA, vectorB) < 0:
                return False

        vectorA = points[coordsCount - 1] - center
        vectorB = points[0] - center
        if pseudo_scalar(vectorA, vectorB) < 0:
            return False

        return True

    @staticmethod
    def _filter_points_by_indices(points: np.ndarray, indices: list) -> np.ndarray:
        indicesLen = len(indices)
        filteredPoints = np.zeros((indicesLen, 2), dtype=np.float32)
        for idx in range(indicesLen):
            filteredPoints[idx] = points[indices[idx]]

        return filteredPoints
