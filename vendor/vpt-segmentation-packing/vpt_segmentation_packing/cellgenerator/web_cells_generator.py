"""Module that loaded prepared packed polygons and transferring them to lod-level z-plane output buffers"""
import sys

import numpy as np

from vpt_segmentation_packing.data.web_polygon_manager import WebLodLevel, WebPolygonManager
from vpt_segmentation_packing.util.general_data import MAX_WEB_TILE_SIZE, grid_size_calculate


class WebCellGenerator:
    """Class for transferring field of view cell data to required visualization
    binary cell data.
    """

    def __init__(self, slicesCount: int):
        self._slicesCount = slicesCount
        # List lod levels of list z-slices of dict: tile-number
        self._linesGrid: list[list[dict[int, list[bytearray]]]] = []
        self._indicesGrid: list[list[dict[int, list]]] = []

        self._cellNumbersGrid: list[list[dict[int, bytearray]]] = []
        self._gridSize: list[tuple[int, int]] = []
        self._gridTileCounts: list[int] = []

    def get_grid_size(self):
        """
        Returns:
             List of tiles sizes for all lod levels.
        """
        return self._gridSize

    def get_cells_by_lod(self, lodLevel: WebLodLevel, zSlice: int) -> list:
        """
        Returns:
             List of bytearrays of transferred-cells for current lod_level.
        """

        return self._build_tiles_btr(lodLevel, zSlice)

    def _init_grid(self, textureSize: tuple[int, int], transformMatrix: np.ndarray):
        for lodLevel in range(WebLodLevel.COUNT.value):
            self._linesGrid.append([])
            self._indicesGrid.append([])
            self._cellNumbersGrid.append([])

            self._gridSize.append(grid_size_calculate(textureSize, transformMatrix, MAX_WEB_TILE_SIZE[lodLevel]))
            tilesCount = self._gridSize[lodLevel][0] * self._gridSize[lodLevel][1]
            self._gridTileCounts.append(tilesCount)

            for z_slice in range(self._slicesCount):
                self._linesGrid[lodLevel].append({})
                self._indicesGrid[lodLevel].append({})
                self._cellNumbersGrid[lodLevel].append({})
                for tileNumber in range(self._gridTileCounts[lodLevel]):
                    self._linesGrid[lodLevel][z_slice][tileNumber] = []
                    self._indicesGrid[lodLevel][z_slice][tileNumber] = []
                    self._cellNumbersGrid[lodLevel][z_slice][tileNumber] = bytearray()

    def set_data(
        self,
        polyList: list[WebPolygonManager],
        texWidth: int,
        texHeight: int,
        transformMatrix: np.ndarray,
        cellIndices: list[str],
    ):
        """Fill tile grid with polygonSets (from polyList).

        :param polyList: List of polygonSets.
        :param texWidth: original texture width.
        :param texHeight: original texture height.
        :param transformMatrix: transformation matrix from experiment domain to texture domain.
        :param cellIndices: list - cells names.
        """

        self._init_grid((texWidth, texHeight), transformMatrix)

        cellId: dict[str, int] = {}
        for i, cell_id in enumerate(cellIndices):
            cellId[str(cell_id)] = i

        # load polygons
        for poly in polyList:
            cellSpatialId = poly.get_spatial_id()
            cellSpatialNumber = cellId.get(cellSpatialId)
            if cellSpatialNumber is None:
                print(f"There is no spatial Id {cellSpatialId} in cell meta data table")
                sys.exit(1)
            cellNumber = np.uint32(cellSpatialNumber)

            zSlice = poly.get_z()
            for lodLevelValue in range(WebLodLevel.COUNT.value):
                if not poly.get_poly_existence(lodLevelValue):  # polygon does not pass filtration
                    continue

                xTile, yTile = poly.get_xy(lodLevelValue)
                tileNumber = yTile * self._gridSize[lodLevelValue][0] + xTile

                linesBtr: bytearray = poly.get_lines(lodLevelValue)

                if lodLevelValue < 2:  # for lod 2 we don't need indices
                    indices = poly.get_indices(lodLevelValue)
                    self._indicesGrid[int(lodLevelValue)][zSlice][tileNumber].extend(indices)

                self._cellNumbersGrid[int(lodLevelValue)][zSlice][tileNumber].extend(cellNumber.tobytes())
                self._linesGrid[lodLevelValue][zSlice][tileNumber].append(linesBtr)

        # set tiles of polygons additional information
        self._set_tiles_antecedent_info()

    def _set_tiles_antecedent_info(self) -> None:
        """Adds to every tile bytearray 2 fields: corner tile point,
        count of polygons in current tile."""
        for lodLevel in range(WebLodLevel.COUNT.value):
            for zSlice in range(self._slicesCount):
                for tileNumber in range(self._gridTileCounts[lodLevel]):
                    xTile = tileNumber % self._gridSize[lodLevel][0]
                    yTile = tileNumber // self._gridSize[lodLevel][0]
                    finalTileBtr = bytearray()
                    finalTileBtr.extend(np.float32(xTile / self._gridSize[lodLevel][0]).tobytes())
                    finalTileBtr.extend(np.float32(yTile / self._gridSize[lodLevel][1]).tobytes())

                    polygonsCount = np.uint32(len(self._linesGrid[int(lodLevel)][zSlice][tileNumber]))
                    finalTileBtr.extend(polygonsCount.tobytes())

                    self._linesGrid[int(lodLevel)][zSlice][tileNumber].insert(0, finalTileBtr)

                    if lodLevel > 1:  # for 0 and 1 lods calculate indices
                        continue

    def _build_tiles_btr(self, lodLevel: WebLodLevel, zSlice: int) -> list[bytearray]:
        tiledList = []
        for tileNumber in range(self._gridTileCounts[lodLevel.value]):
            output_btr = bytearray()
            output_btr.extend(b"".join(self._linesGrid[int(lodLevel.value)][zSlice][tileNumber]))
            output_btr.extend(self._cellNumbersGrid[int(lodLevel.value)][zSlice][tileNumber])

            if lodLevel in [WebLodLevel.LOD0, WebLodLevel.LOD1]:
                output_btr.extend(self._indicesGrid[int(lodLevel.value)][zSlice][tileNumber])

            tiledList.append(output_btr)
        return tiledList
