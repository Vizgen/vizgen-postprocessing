"""Module with class for transferring (partition, filtering, packing) polygon from spatialFeature objects
to WebPolygonManager objects.
"""
import numpy as np
from shapely import geometry

from vpt_segmentation_packing.data.raw_cell import Feature
from vpt_segmentation_packing.data.web_polygon_manager import WebLodLevel, WebPolygonManager
from vpt_segmentation_packing.util.general_data import MAX_WEB_TILE_SIZE, grid_size_calculate


class CellTransfer:
    """Class for transferring spatialFeature objects to WebPolygonManager objects."""

    def __init__(self, textureWidth: int, textureHeight: int, transformationMatrix: np.ndarray):
        self._textureSize = (textureWidth, textureHeight)
        self._transformMatrix = transformationMatrix
        self._expBbox = (textureWidth / transformationMatrix[0][0], textureHeight / transformationMatrix[1][1])

        self._desktopGridSize = grid_size_calculate((textureWidth, textureHeight), transformationMatrix, 400)
        self.gridPolyCounts = self._desktopGridSize[0] * self._desktopGridSize[1]

        self._webGridSize = []
        for lodLevel in range(WebLodLevel.COUNT.value):
            self._webGridSize.append(
                grid_size_calculate((textureWidth, textureHeight), transformationMatrix, MAX_WEB_TILE_SIZE[lodLevel])
            )

    def process_cells(self, spatialList: list[Feature]) -> list[WebPolygonManager]:
        """Transfers polygons from spatialFeature objects to PolygonSet objects.

        :param spatialList: List of spatial features.
        :return: List of polygons (objects of PolygonSet class).
        """
        webPolygonsList = []
        for spatial in spatialList:
            for z_slice, zSlicePoly in enumerate(spatial.shapes):
                if zSlicePoly is None or zSlicePoly.is_empty:
                    continue
                poly: geometry.Polygon = zSlicePoly.geoms[0]

                spatial_id = str(spatial.get_feature_id())

                true_coords = np.column_stack(poly.exterior.coords.xy)

                webPolygon = WebPolygonManager(z_slice, spatial_id)

                poly_relevant_reduce = webPolygon.points_transform(
                    true_coords, self._transformMatrix, self._textureSize, self._webGridSize
                )

                if poly_relevant_reduce:
                    webPolygonsList.append(webPolygon)

        return webPolygonsList
