import math
from typing import Dict, List, Tuple, Optional

import numpy as np
from vpt_core import log

from vpt.update_vzg.byte_utils import extend_with_u32, extend_with_i16, extend_with_i32
from vpt.update_vzg.cell_metadata import CellMetadata
from vpt.update_vzg.imageparams import ImageParams
from vpt.update_vzg.polygons.packedfanpolygon import PackedFanPolygon
from vpt.update_vzg.polygons.packedpolygon import LodLevel
from vpt.update_vzg.polygons.packedstarpolygon import PackedStarPolygon
from vpt.update_vzg.polygons.polygonset import PolygonSet
from vpt.utils.general_data import grid_size_calculate
from vpt.utils.raw_cell import Feature


class CellTransfer:
    """Class for transferring spatialFeature objects to PolygonSet objects."""

    def __init__(self, imageParams: ImageParams):
        self._mtpMatrix = imageParams.micronToPixelMatrix
        self._textureSize = imageParams.textureSize

        self._expBbox = (self._textureSize[0] / self._mtpMatrix[0][0], self._textureSize[1] / self._mtpMatrix[1][1])
        self._gridSize = grid_size_calculate(self._textureSize, self._mtpMatrix)
        self.gridPolyCounts = self._gridSize[0] * self._gridSize[1]

    def process_cells(self, rawCellsList: List[Feature], fovIdx: int) -> List[PolygonSet]:
        """Transfer points: thinning out, transformation to the new domain"""
        polygonsList = []
        for rawCell in rawCellsList:
            for z_slice, zSlicePoly in enumerate(rawCell.shapes):
                if zSlicePoly is None or zSlicePoly.is_empty:
                    continue
                poly = zSlicePoly.geoms[0]
                rawId = rawCell.get_feature_id()
                x_center, y_center = poly.centroid.x, poly.centroid.y

                true_coords = np.column_stack(poly.exterior.coords.xy)
                polygon = PolygonSet(z_slice, x_center, y_center, rawId)
                poly_relevant_reduce = polygon.points_transform(
                    true_coords, self._mtpMatrix, self._textureSize, self._gridSize, self._expBbox
                )

                if poly_relevant_reduce:
                    polygonsList.append(polygon)

        log.info(f"Done fov {fovIdx}")
        return polygonsList


class CellsTransfer:
    def __init__(self, cell_metadata: CellMetadata, z_count: int, image_params: ImageParams):
        self._zCount = z_count
        self.grid: List[Dict[int, List[PolygonSet]]] = []

        self._cellMetadata = cell_metadata
        self._cellsIdDict: Dict[str, int] = {v: i for [i, v] in enumerate(cell_metadata.get_names_array())}

        self._cellsCount = len(self._cellsIdDict)
        self.pointersToPolys: Optional[np.ndarray] = None

        self._mtpMatrix = image_params.micronToPixelMatrix
        self._textureSize = image_params.textureSize
        self._gridSize = grid_size_calculate(image_params.textureSize, image_params.micronToPixelMatrix)
        self._init_grid()

    def get_z_panes_count(self):
        return self._zCount

    def _init_grid(self):
        for z_slice in range(self._zCount):
            self.grid.append({})
            for key in range(self._gridSize[0] * self._gridSize[1]):
                self.grid[z_slice][key] = []

    def fill_grid(self, poly_list: List[PolygonSet]):
        """Associate voxels with cells"""
        gridSize = self._gridSize[0] * self._gridSize[1]
        mtpMatrix = self._mtpMatrix
        for polySet in poly_list:
            p: PolygonSet = polySet
            (cx, cy, z) = p.get_center()
            spatId = p.get_spatial_id()
            p.set_cell_id(self._cellsIdDict[spatId])
            x_ind: int = math.floor((cx * mtpMatrix[0][0] + mtpMatrix[0][2]) / self._textureSize[0] * self._gridSize[0])
            y_ind: int = math.floor(
                (1.0 - (cy * mtpMatrix[1][1] + mtpMatrix[1][2]) / self._textureSize[1]) * self._gridSize[1]
            )

            gridNumber = y_ind * self._gridSize[0] + x_ind
            if gridNumber < 0 or gridNumber >= gridSize:
                log.warning(
                    f"Poly with coordinates {cx} and {cy} is out of the area. Z is {z}, id: {spatId}."
                    f" Getting grid coordinates {x_ind} and {y_ind}"
                )
                continue
            self.grid[z][gridNumber].append(polySet)

    def get_cells_by_lod(self, lodLevel: LodLevel) -> list:
        """
        Returns:
             List of bytearrays of transferred-cells for current lod_level.
        """
        self.pointersToPolys = np.zeros((self._cellsCount, self._zCount, 2), dtype=np.uint32)

        cellsLodList = []
        for z_slice in range(self._zCount):
            packedPolygonsDict: List[List] = [[], [], [], []]
            blocksCount = np.zeros(4, np.uint32)
            polyVoxelGrid: List = [bytearray(), bytearray(), bytearray(), bytearray()]
            # Step 5. Fill output buffers
            self._make_points_buffer(lodLevel, z_slice, packedPolygonsDict, polyVoxelGrid, blocksCount)

            cellsLodList.append(self._build_cells_btr(lodLevel, packedPolygonsDict, polyVoxelGrid))

        return cellsLodList

    def _make_points_buffer(self, lodLevel, zSlice, packedPolygonsDict, polyVoxelGrid, blocksCount):
        polyIdx = [0, 0, 0, 0]

        for polygons in self.grid[zSlice].values():
            polyInVoxel = [0, 0, 0, 0]

            for packSize in range(4):
                polyVoxelGrid[packSize].extend(np.int32(polyIdx[packSize]))

            for curr_poly in polygons:  # type: PolygonSet
                cellId = curr_poly.get_cell_id()
                polyType, packedPolygonsBytes = curr_poly.get_packed_bytes(lodLevel)

                if polyType >= 0:
                    packedPolygonsDict[polyType].append(packedPolygonsBytes)

                    polyInVoxel[polyType] += 1

                    self.pointersToPolys[cellId][zSlice][0] = polyType + 1
                    if lodLevel == LodLevel.Min:
                        self.pointersToPolys[cellId][zSlice][0] = 1

                    self.pointersToPolys[cellId][zSlice][1] = blocksCount[polyType]
                    blocksCount[polyType] += 1

            for packSize in range(4):
                polyVoxelGrid[packSize].extend(np.int32(polyInVoxel[packSize]))
                polyIdx[packSize] += polyInVoxel[packSize]

    @staticmethod
    def _build_cells_btr(lodLevel, packedPolygonsDict, polyVoxelGrid) -> bytearray:
        output_btr = bytearray()
        # ----  Header ----
        packedPolyBtrDict = {}

        for packSizeType in range(3):
            if lodLevel == LodLevel.Min:
                extend_with_u32(output_btr, 0)
                continue

            packedPolyBtrDict[packSizeType] = b"".join(packedPolygonsDict[packSizeType])
            packedPolySize = PackedStarPolygon.get_bytes_count(lodLevel, packSizeType)
            if packedPolySize != 0:
                extend_with_u32(output_btr, (len(packedPolyBtrDict[packSizeType]) / packedPolySize))
            else:
                extend_with_u32(output_btr, 0)

        packedFanPolygons = b"".join(packedPolygonsDict[3])
        packedPolySize = PackedFanPolygon.Bytes_Count[lodLevel.value]
        if packedPolySize != 0:
            extend_with_u32(output_btr, len(packedFanPolygons) / packedPolySize)
        else:
            extend_with_u32(output_btr, 0)

        # ----  Data ----
        if not lodLevel == LodLevel.Min:
            for packSize in range(3):
                output_btr.extend(packedPolyBtrDict[packSize])
        output_btr.extend(packedFanPolygons)

        if not lodLevel == LodLevel.Min:
            for packSize in range(3):
                output_btr.extend(polyVoxelGrid[packSize])
        output_btr.extend(polyVoxelGrid[3])

        return output_btr

    def get_poly_pointer_arrays(self) -> Tuple[bytearray, bytearray]:
        """
        Returns:
             (cell-array bytearray, polygon-pointer-array bytearrays).
        """
        pointersToPolyBtr = bytearray()
        cellArray = bytearray()
        cellIndex = 0
        if self.pointersToPolys is None:
            raise ValueError("State of CellsTransfer class is broken: pointersToPolys field is None")
        for _, cell in enumerate(self.pointersToPolys):
            zSliceCount = 0
            for zSlice, zSliceData in enumerate(cell):
                if zSliceData[0] != 0:
                    extend_with_u32(pointersToPolyBtr, zSliceData[1])
                    extend_with_i16(pointersToPolyBtr, zSliceData[0] - 1)
                    extend_with_i16(pointersToPolyBtr, zSlice)
                    zSliceCount += 1
            extend_with_u32(cellArray, cellIndex)
            extend_with_i32(cellArray, zSliceCount)
            cellIndex += zSliceCount

        return pointersToPolyBtr, cellArray
