from typing import List

from shapely import geometry


class Feature:
    def __init__(self, rawCellId: str, rawPolysGeometryList: List[List[geometry.shape]]):
        self.shapes: List[geometry.shape or None] = rawPolysGeometryList
        self.id = rawCellId

    def get_feature_id(self):
        return self.id

    def get_boundaries(self, zPlane: int = 0):
        return self.shapes[zPlane]

    def get_true_polygons(self):
        return list(filter(lambda shape: shape is not None, self.shapes))

    def get_full_cell(self) -> List:
        """Add empty polygon on z planes without polygons"""
        output = []
        for shape in self.shapes:
            if shape is not None:
                output.append(shape)
            else:
                output.append(geometry.Polygon(((0, 0), (0, 0), (0, 0))))
        return output
