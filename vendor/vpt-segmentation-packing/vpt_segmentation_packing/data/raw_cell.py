from typing import Union

import shapely


class Feature:
    def __init__(self, rawCellId: Union[int, str], rawPolysGeometryList: list[Union[shapely.MultiPolygon, None]]):
        self.shapes = rawPolysGeometryList
        self.id = rawCellId

    def get_feature_id(self) -> Union[int, str]:
        return self.id

    def get_boundaries(self, zPlane: int = 0) -> Union[shapely.MultiPolygon, None]:
        return self.shapes[zPlane]

    def get_true_polygons(self) -> list[shapely.MultiPolygon]:
        return list(filter(lambda shape: shape is not None, self.shapes))
