"""Module with abstract class for filtering and packing web and desktop polygons"""
import numpy as np

from vpt_segmentation_packing.util.vector_operations import pseudo_scalar


def l2_dist_sqr(deltaX, deltaY):
    """
    Returns:
         L2 squared norm of 2 dimensions.
    """
    return deltaX * deltaX + deltaY * deltaY


class PolygonManager:
    """Abstract class with base set of filtering polygon functions, the same
    for desktop and web versions."""

    THINNING_BIT_FACTOR = 1 << 20

    def __init__(self, zSlice: int, spatial_id: str = ""):
        self._zSlice: int = zSlice
        self._spatialId = spatial_id

    def get_spatial_id(self) -> str:
        """Get cell name (spatial id).
        Returns:
             spatial id.
        """
        return self._spatialId

    @staticmethod
    def _thinning_web(points: np.ndarray) -> np.ndarray:
        """Remove identical points after transferring them from pixels domain.

        Args:
            points: (np.ndarray): 2-dimensional array of polygon points in
            pixel domain [textureWidth, textureHeight]
        Returns:
            np.ndarray: 2-dimensional array of polygon points in
            pixel domain [textureWidth, textureHeight]
        """
        x_start_number = points[0][0]
        y_start_number = points[0][1]
        x_prev_number, y_prev_number = x_start_number, y_start_number

        thinned_bool_filter_arr = [True]

        iter_coords = iter(points)
        next(iter_coords)

        for coords in iter_coords:
            x_curr_number = coords[0]
            y_curr_number = coords[1]

            thinned_bool_filter_arr.append(not (x_curr_number == x_prev_number and y_curr_number == y_prev_number))

            x_prev_number = x_curr_number
            y_prev_number = y_curr_number

        # last point
        x_curr_number = x_start_number
        y_curr_number = y_start_number
        thinned_bool_filter_arr[0] = not (x_curr_number == x_prev_number and y_curr_number == y_prev_number)

        return points[thinned_bool_filter_arr]

    @staticmethod
    def _scaling_web(points: np.ndarray, transformMatrix: np.ndarray) -> None:
        """Scale points from experiment domain (um) to pixel (texture) domain.
        (Revert y-axe, to be consistent with images).

        Args:
            np.ndarray: 2-dimensional array of polygon points in
            texture domain (pixels).
        """

        for point in points:
            x_texture = point[0] * transformMatrix[0][0] + transformMatrix[0][2]
            y_texture = point[1] * transformMatrix[1][1] + transformMatrix[1][2]

            point[0] = np.int32(x_texture)
            point[1] = np.int32(y_texture)

    @staticmethod
    def _find_next_not_reduced_vertex(trueVerticesList: list[bool], ind: int) -> int:
        n = len(trueVerticesList)
        while ind < n and not trueVerticesList[ind]:
            ind += 1

        return ind

    def _vertex_level_reduce(self, points: np.ndarray, pointsThreshold: int) -> np.ndarray:
        """Removes points until their count become equal to pointsThreshold.

        On each step algorithm find the minimum distance between 2 points,
        after that replace these 2 points to 1 that relocated between them.
        Complexity is O(n^2).

        Args:
            points: (np.ndarray): 2-dimensional array of polygon points in
            unify domain [0, 1]
            pointsThreshold: int: points count after this reducing
        Returns:
            np.ndarray: 2-dimensional array of polygon points in
            unify domain [0, 1] after reducing their count to pointsThreshold
        """
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
    def _one_straight_points_reduction(points: np.ndarray) -> np.ndarray:
        """Remove points laying on one straight.

        Args:
            points: (np.ndarray): 2-dimensional array of polygon points in
            pixel domain [textureWidth, textureHeight]
        Returns:
            np.ndarray: 2-dimensional array of polygon points in
            pixel domain [textureWidth, textureHeight]
        """

        n = len(points)
        oneLinePoints = np.ones(n, dtype=np.bool_)
        pointA = points[0]
        for pointIdx in range(1, n):
            pointB = points[pointIdx]
            pointC = points[(pointIdx + 1) % n]

            # check for point B on one line with points A, B
            if pseudo_scalar(pointA - pointB, pointC - pointB) == 0:
                oneLinePoints[pointIdx] = False

            pointA = pointB

        return points[oneLinePoints]
