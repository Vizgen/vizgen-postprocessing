import numpy as np

from vpt.update_vzg.polygons.polystructers import IndexedPolygon, PointsIndices
from vpt.update_vzg.polygons.vector_operations import (
    dot_2d,
    find_bisector,
    point_in_sector,
    point_line_side,
    pseudo_scalar,
    ray_segment_intersect,
    segment_outline_intersect,
)


class PolyPartition:
    """Class for part original polygon into fan polygons."""

    def __init__(self, originPoints: np.ndarray):
        """Args:
        originPoints: List[np.array] - list of 2-dims (numpy array) points
        """
        self._originPoints = originPoints.copy()
        self._originPointsLen = len(self._originPoints)

    def _find_concave_point(self, pointsIdx: list, startPointIdx=0) -> list:
        origins = self._originPoints
        concavePointsIdxList = []
        n = len(pointsIdx)
        pointA = origins[pointsIdx[(n - 1 + startPointIdx) % n]]
        for pointIdx in range(n):
            pointB = origins[pointsIdx[(pointIdx + startPointIdx) % n]]
            pointC = origins[pointsIdx[(pointIdx + startPointIdx + 1) % n]]

            # check for "bad" (concave) point
            if pseudo_scalar(pointA - pointB, pointC - pointB) > 0:
                concavePointsIdxList.append((pointIdx + startPointIdx) % n)

            pointA = pointB

        return concavePointsIdxList

    def get_origins(self):
        """Returns original polygon coordinates."""
        return self._originPoints

    def _find_intersect_segment(self, pointsIdx, supportPointIdx, ABCBisector):
        n = len(pointsIdx)
        B = self._originPoints[pointsIdx[supportPointIdx]]
        BB = B + ABCBisector
        minDistance = float("inf")
        segmentAIdx, segmentBIdx = -1, -1
        minDistPointIdx = -1
        minDistBetweenPoints = 10e10
        leftPoint = self._originPoints[pointsIdx[(supportPointIdx - 1) % n]]
        rightPoint = self._originPoints[pointsIdx[(supportPointIdx + 1) % n]]
        for i in range(n - 2):
            indE = (supportPointIdx + i + 1) % n
            indF = (supportPointIdx + i + 2) % n
            E = self._originPoints[pointsIdx[indE]]
            F = self._originPoints[pointsIdx[indF]]
            lineSideLeftPoint = point_line_side(F, B, leftPoint)
            lineSideRightPoint = point_line_side(F, B, rightPoint)

            if (not (lineSideLeftPoint >= 0 and lineSideRightPoint <= 0)) and i != n - 3:
                distBetweenPoints = np.linalg.norm(B - F)
                if minDistBetweenPoints > distBetweenPoints:
                    minDistBetweenPoints = distBetweenPoints
                    minDistPointIdx = indF

            if point_line_side(E, B, BB) <= 0 and point_line_side(F, B, BB) >= 0:
                p = ray_segment_intersect(B, ABCBisector, E, F)
                vp = p - B
                if dot_2d(vp, ABCBisector) > 0:
                    dist2 = dot_2d(vp, vp)
                    if minDistance > dist2:
                        minDistance = dist2
                        segmentAIdx = indF
                        segmentBIdx = indE

        return segmentAIdx, segmentBIdx, minDistPointIdx

    def _cut_from_concave_point(self, pointsIndices: PointsIndices, ind: int):
        pointsIdx = pointsIndices.polyIndices
        origins = self._originPoints
        n = len(pointsIdx)
        pointA = origins[pointsIdx[(ind - 1) % n]]
        pointB = origins[pointsIdx[ind]]
        pointC = origins[pointsIdx[(ind + 1) % n]]
        ABVec = pointB - pointA
        CBVec = pointB - pointC

        # find the bisector
        ABCBisector = find_bisector(ABVec, CBVec)

        # find intersects segment
        segmentAIdx, segmentBIdx, minDistPointIdx = self._find_intersect_segment(pointsIdx, ind, ABCBisector)
        if segmentAIdx < 0 or segmentBIdx < 0 or minDistPointIdx < 0:
            raise IndexError

        intersectAVec = origins[pointsIdx[segmentAIdx]] - pointB
        if point_in_sector(intersectAVec, CBVec, ABVec) and not segment_outline_intersect(
            origins, ind, segmentAIdx, pointsIdx, False
        ):
            # create new polygons
            leftPoly, rightPoly = pointsIndices.polygon_partition(ind, segmentAIdx)
        else:
            intersectBVec = origins[pointsIdx[segmentBIdx]] - pointB
            if point_in_sector(intersectBVec, CBVec, ABVec) and not segment_outline_intersect(
                origins, ind, segmentBIdx, pointsIdx
            ):
                # create new polygons
                leftPoly, rightPoly = pointsIndices.polygon_partition(ind, segmentBIdx)
            else:
                # create new polygons
                leftPoly, rightPoly = pointsIndices.polygon_partition(ind, minDistPointIdx)

        return leftPoly, rightPoly

    def _get_single_result_from_list(self, pointsIdx: PointsIndices):
        concavePointsIdx = self._find_concave_point(pointsIdx.polyIndices)
        if len(concavePointsIdx) == 0:
            return concavePointsIdx, IndexedPolygon("convex", pointsIdx.polyIndices, pointsIdx.includePoints, -1)

        if len(concavePointsIdx) == 1:
            return concavePointsIdx, IndexedPolygon(
                "fan", pointsIdx.polyIndices, pointsIdx.includePoints, concavePointsIdx[0]
            )

        for ci in concavePointsIdx:
            if self._is_all_edges_visible(self._originPoints[pointsIdx.polyIndices[ci]], pointsIdx.polyIndices):
                return concavePointsIdx, IndexedPolygon("fan", pointsIdx.polyIndices, pointsIdx.includePoints, ci)

        return concavePointsIdx, None

    def run_partition(self, out):
        """Runs full pipeline of polygon partition, including split polygon
        into fans polygons, and merge them into bigger fan polygons,
        if it is possible.
        """
        pointsIndices = PointsIndices(list(range(len(self._originPoints))))
        self.split_polygon(pointsIndices, out)
        self.merge_postproces(out)

    def split_polygon(self, pointsIdx: PointsIndices, out, depth=0):
        """Recursive splits polygons while they are not fan polygons
        Args:
            pointsIdx: indices in self._originPoints,
            of current considered polygon
            out: list of already parted fan polygons (only indices)
            depth: recursion depth.
        """
        if depth > 20:  # we get stuck because of wrong origin poly
            raise TimeoutError

        (concavePoints, one) = self._get_single_result_from_list(pointsIdx)

        if one is not None:
            out.append(one)
        else:
            cidx = concavePoints[len(concavePoints) // 2]
            (l, r) = self._cut_from_concave_point(pointsIdx, cidx)
            self.split_polygon(l, out, depth + 1)
            self.split_polygon(r, out, depth + 1)

    def _merge_results(self, p1, p2, i1, i2):
        polyIndices = p1.polyIndices[:i1] + p2.polyIndices[i2 + 1 :] + p2.polyIndices[:i2] + p1.polyIndices[i1 + 1 :]

        includeIndices1 = p1.includeIndices.copy()
        includeIndices2 = p2.includeIndices.copy()
        includeIndices1[i1] = True
        includeIndices2[i2] = True

        includePoints = (
            includeIndices1[:i1] + includeIndices2[i2 + 1 :] + includeIndices2[:i2] + includeIndices1[i1 + 1 :]
        )

        pointsIdx = PointsIndices(polyIndices, includePoints)

        if p1.type == "convex" and p2.type == "convex":
            return IndexedPolygon("fan", pointsIdx.polyIndices, pointsIdx.includePoints, i1)
        (_, ret) = self._get_single_result_from_list(pointsIdx)
        return ret

    def merge_postproces(self, results: list):
        """Merge fan polygons into bigger fan polygons if it is possible."""
        concavePoints = self._find_concave_point(list(range(len(self._originPoints))))

        for cindex in concavePoints:
            candidates = []
            for rindex, res in enumerate(results):
                for i, pIdx in enumerate(res.polyIndices):
                    if cindex == pIdx:
                        candidates.append((rindex, i))
                        break
            merged = []
            for fi in range(len(candidates) - 1):
                fpointsIdx = results[candidates[fi][0]].polyIndices
                findex = candidates[fi][1]
                for si in range(fi + 1, len(candidates)):
                    if candidates[si][0] in merged or candidates[fi][0] in merged:
                        continue

                    spointsIdx = results[candidates[si][0]].polyIndices
                    sindex = candidates[si][1]
                    mresult = None
                    if fpointsIdx[(findex - 1) % len(fpointsIdx)] == spointsIdx[(sindex + 1) % len(spointsIdx)]:
                        mresult = self._merge_results(
                            results[candidates[fi][0]],
                            results[candidates[si][0]],
                            (findex - 1) % len(fpointsIdx),
                            sindex,
                        )

                    elif fpointsIdx[(findex + 1) % len(fpointsIdx)] == spointsIdx[(sindex - 1) % len(spointsIdx)]:
                        mresult = self._merge_results(
                            results[candidates[fi][0]],
                            results[candidates[si][0]],
                            findex,
                            (sindex - 1) % len(spointsIdx),
                        )
                    if mresult is not None:
                        merged.append(candidates[fi][0])
                        merged.append(candidates[si][0])
                        results.append(mresult)

            # clean merged
            for index in sorted(merged, reverse=True):
                del results[index]

    @staticmethod
    def _get_bbox(points):
        return [np.min(points, axis=0), np.max(points, axis=0)]

    def _is_all_edges_visible(self, point, pointsIdx) -> bool:
        pointsLen = len(pointsIdx)
        a = self._originPoints[pointsIdx[len(pointsIdx) - 1]]
        for i in range(pointsLen):
            b = self._originPoints[pointsIdx[i]]
            s = point_line_side(point, a, b)
            if s < 0:
                return False
            a = b
        return True

    def _get_star_center(self, pointsIdx):
        bbox = PolyPartition._get_bbox(list(self._originPoints[i] for i in pointsIdx))
        center = (bbox[0] + bbox[1]) * 0.5
        n = len(pointsIdx)
        if n < 4 or self._is_all_edges_visible(center, pointsIdx):
            return center
        return None
