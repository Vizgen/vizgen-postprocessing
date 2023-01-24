from typing import Tuple
from collections import namedtuple

IndexedPolygon = namedtuple(
    'IndexedPolygon', 'type polyIndices includeIndices ind')


class PointsIndices:
    """Class for storing list of indices of original poly, that represent
    some parted polygon."""

    def __init__(self, polyIndices, includePoints=None):
        self.polyIndices = polyIndices
        if includePoints is not None:
            self.includePoints = includePoints
        else:
            self.includePoints = [True] * len(polyIndices)

    def polygon_partition(self, startIdx, endIdx) -> Tuple['PointsIndices', 'PointsIndices']:
        """Parts this polygon into 2 new polygons.
        Args:
            startIdx: index in this polygon that will be 0-index in the
            left new polygon.
            endIdx: index in this polygon that will be the last index in the
            left new polygon.
        Returns:
             (left new polygon, right new polygon).
        """
        leftPolyIndices = []
        rightPolyIndices = []

        leftPolyIncludes = []
        rightPolyIncludes = []

        n = len(self.polyIndices)
        idx = startIdx
        while idx != endIdx:
            rightPolyIndices.append(self.polyIndices[idx])
            rightPolyIncludes.append(self.includePoints[idx])
            idx = (idx + 1) % n
        rightPolyIndices.append(self.polyIndices[endIdx])
        rightPolyIncludes.append(False)

        idx = endIdx
        while idx != startIdx:
            leftPolyIndices.append(self.polyIndices[idx])
            leftPolyIncludes.append(self.includePoints[idx])
            idx = (idx + 1) % n
        leftPolyIndices.append(self.polyIndices[startIdx])
        leftPolyIncludes.append(False)

        return PointsIndices(leftPolyIndices, leftPolyIncludes), \
               PointsIndices(rightPolyIndices, rightPolyIncludes) # noqa
