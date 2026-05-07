import numpy as np

from vpt_segmentation_packing.util.vector_operations import pseudo_scalar


def left_top_index(points):
    minIdx = 0
    for i in range(1, len(points)):
        if points[i][0] < points[minIdx][0]:
            minIdx = i
        elif points[i][0] == points[minIdx][0]:
            if points[i][1] > points[minIdx][1]:
                minIdx = i
    return minIdx


def on_segment(p, q, r):
    """If points p, q, r are collinear checks if q between p and q"""
    return max(p[0], r[0]) >= q[0] >= min(p[0], r[0]) and max(p[1], r[1]) >= q[1] >= min(p[1], r[1])


def build_convex_hull(points: np.ndarray) -> list:
    """Builds Jarvis convex hull"""

    n = len(points)
    hullIndices: list = []
    leftXPointIdx = left_top_index(points)
    suppPointIdx = leftXPointIdx
    while True:
        hullIndices.append(suppPointIdx)

        mostRightPointIdx = (suppPointIdx + 1) % n

        for i in range(n):
            orient = pseudo_scalar(points[suppPointIdx] - points[i], points[mostRightPointIdx] - points[i])
            if orient < 0:
                mostRightPointIdx = i

            elif (
                suppPointIdx != i
                and orient == 0
                and on_segment(points[suppPointIdx], points[mostRightPointIdx], points[i])
            ):
                mostRightPointIdx = i

        suppPointIdx = mostRightPointIdx
        if suppPointIdx == leftXPointIdx:
            break

    return hullIndices
