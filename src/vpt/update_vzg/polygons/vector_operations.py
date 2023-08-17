import math
from typing import Tuple

import numpy as np


# https://bryceboe.com/2006/10/23/line-segment-intersection-algorithm/
def ccw(a, b, c):
    """Returns true if three points (a, b, c) are listed in a counterclockwise
    order.
    """
    return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])


def segments_intersects(A, B, C, D):
    """Returns true if segments AB and CD intersects."""
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)


def find_bisector(AB, BC) -> np.ndarray:
    """Finds bisector of angle, obtained by two vectors: AB and BC.
    Returns:
        (np.array) bisector unitary vector.
    """
    v = AB / np.linalg.norm(AB) + BC / np.linalg.norm(BC)
    return v / np.linalg.norm(v)


def pseudo_scalar(vectorA, vectorB):
    """Calculates pseudo scalar multiplication between vectorA and vectorB."""
    return vectorA[0] * vectorB[1] - vectorB[0] * vectorA[1]


def point_in_sector(pointVec, leftSectorDir, rightSectorDir) -> bool:
    """Determines if pointVec is between leftSectorDir and rightSectorDir."""
    return pseudo_scalar(pointVec, leftSectorDir) >= 0 and pseudo_scalar(pointVec, rightSectorDir) <= 0  # noqa


def ray_segment_intersect(pointO, ray, pointA, pointB) -> np.ndarray:
    """Determines if ray started from  pointO intersects segment with points
    pointA and pointB.
    """
    v1 = pointO - pointA
    v2 = pointB - pointA

    v3 = np.array([-ray[1], ray[0]])
    if np.dot(v2, v3) == 0:
        return pointO

    t = np.cross(v2, v1) / np.dot(v2, v3)

    return pointO + ray * t


def point_segment_distance(pointO, ray, pointA, pointB):
    """Calculates distance between pointO and point on segment with points
    pointA and pointB, which is intersection of ray started from  pointO and
    segment with points pointA and pointB.
    """
    pointOnSegment = ray_segment_intersect(pointO, ray, pointA, pointB)
    return np.linalg.norm(pointOnSegment - pointO)


def point_line_side(point, A, B) -> int:
    """Returns points side replacing with respect to AB line.
    Returns:
        0: if point is on AB line
        +1: if point is left-side to AB
        -1: if point is right-side to AB
    """
    return np.sign((B[0] - A[0]) * (point[1] - A[1]) - (B[1] - A[1]) * (point[0] - A[0]))


def dot_2d(a, b):
    """Returns scalar product of 2-dimensions a and b vectors."""
    return a[0] * b[0] + a[1] * b[1]


def segment_outline_intersect(origins, badPointIdx, partedPointIdx, pointsIdx, firstPart=True) -> bool:
    """Checks if segment with points origins[pointsIdx[badPointIdx]] and
    origins[pointsIdx[partedPointIdx]] intersects with polygon outline.
    Args:
        origins: original polygon coordinates.
        badPointIdx: index in pointsIdx, that represents concave point
        partedPointIdx: index in pointsIdx, that represents point, which is
        candidate to part this polygon into 2 polygons (with delimiter
        badPointIdx-partedPointIdx)
        pointsIdx: indices in origins of current polygon.
        firstPart (bool): flag that shows which part of polygon it is needed
        to check with this function.
    """
    n = len(pointsIdx)
    badPoint = origins[pointsIdx[badPointIdx]]
    partedPoint = origins[pointsIdx[partedPointIdx]]

    startIdx = (partedPointIdx + 1) % n
    endIdx = (badPointIdx - 1) % n
    if firstPart:
        startIdx = (badPointIdx + 1) % n
        endIdx = (partedPointIdx - 1) % n

    pointIdx = startIdx
    while pointIdx != endIdx:
        if segments_intersects(
            badPoint, partedPoint, origins[pointsIdx[pointIdx]], origins[pointsIdx[(pointIdx + 1) % n]]
        ):
            return True

        pointIdx = (pointIdx + 1) % n

    return False


def clockwise_traverse(polyCoordinates) -> bool:
    """Determines if points polygon are in clockwise order."""
    traverseSum = 0
    n = len(polyCoordinates)
    for pointIdx in range(n):
        pointA = polyCoordinates[pointIdx]
        pointB = polyCoordinates[(pointIdx + 1) % n]
        traverseSum += (pointB[0] - pointA[0]) * (pointB[1] + pointA[1])

    if traverseSum < 0:
        return False

    return True


def rotate_point(x, y, xCenter, yCenter, angle) -> Tuple[float, float]:
    """Rotates point (x,y) around point (xCenter, yCenter) by angle.
    Returns:
         rotated point.
    """
    p_x = xCenter + (x - xCenter) * math.cos(angle) - (y - yCenter) * math.sin(angle)
    p_y = yCenter + (y - yCenter) * math.cos(angle) + (x - xCenter) * math.sin(angle)

    return p_x, p_y
