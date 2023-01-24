import numpy as np
from typing import List, Dict, Tuple
import math

from vpt.update_vzg.cell_metadata import CellMetadata
from vpt.update_vzg.imageparams import ImageParams

from vpt.update_vzg.polygons.packedfanpolygon import PackedFanPolygon
from vpt.update_vzg.polygons.packedpolygon import LodLevel
from vpt.update_vzg.polygons.packedstarpolygon import PackedStarPolygon
from vpt.update_vzg.polygons.polygonset import PolygonSet
from vpt.utils.raw_cell import Feature
from vpt.utils.general_data import grid_size_calculate


class CellTransfer:
    """Class for transferring spatialFeature objects to PolygonSet objects.
    """

    def __init__(self, imageParams: ImageParams):

        self._mtpMatrix = imageParams.micronToPixelMatrix
        self._textureSize = imageParams.textureSize

        self._expBbox = (self._textureSize[0] / self._mtpMatrix[0][0],
                         self._textureSize[1] / self._mtpMatrix[1][1])
        self._gridSize = grid_size_calculate(self._textureSize, self._mtpMatrix)
        self.gridPolyCounts = self._gridSize[0] * self._gridSize[1]

    def process_cells(self,
                      rawCellsList: List[Feature],
                      fovIdx: int
                      ) -> List[PolygonSet]:
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
                    true_coords, self._mtpMatrix, self._textureSize,
                    self._gridSize, self._expBbox)

                if poly_relevant_reduce:
                    polygonsList.append(polygon)

        print(f'Done fov {fovIdx}')
        return polygonsList


class CellsTransfer:
    def __init__(self, cellMetadata: CellMetadata, zCount: int, imageParams: ImageParams):
        self._zCount = zCount
        self.grid: List[Dict[int:List[PolygonSet]]] = []

        self._cellMetadata = cellMetadata
        self._cellsIdDict: Dict[str: int] = \
            {name: i for i, name in enumerate(cellMetadata.get_names_array())}

        self._cellsCount = len(self._cellsIdDict)
        self.pointersToPolys = None

        self._mtpMatrix = imageParams.micronToPixelMatrix
        self._textureSize = imageParams.textureSize
        self._gridSize = grid_size_calculate(imageParams.textureSize, imageParams.micronToPixelMatrix)
        self._init_grid()

    def get_z_panes_count(self):
        return self._zCount

    def _init_grid(self):
        for z_slice in range(self._zCount):
            self.grid.append({})
            for key in range(self._gridSize[0] * self._gridSize[1]):
                self.grid[z_slice][key] = []

    def fill_grid(self, polyList):
        """Associate voxels with cells"""
        gridSize = self._gridSize[0] * self._gridSize[1]
        mtpMatrix = self._mtpMatrix
        for polySet in polyList:
            p: PolygonSet = polySet
            (cx, cy, z) = p.get_center()
            spatId = p.get_spatial_id()
            p.set_cell_id(self._cellsIdDict[spatId])
            x_ind: int = math.floor(
                (cx * mtpMatrix[0][0] + mtpMatrix[0][2]) / self._textureSize[0] * self._gridSize[0])
            y_ind: int = math.floor(
                (1.0 - (cy * mtpMatrix[1][1] + mtpMatrix[1][2]) / self._textureSize[1]) * self._gridSize[1])

            gridNumber = y_ind * self._gridSize[0] + x_ind
            if gridNumber < 0 or gridNumber >= gridSize:
                print(f'Poly with coordinates {cx} and {cy} is out of the area. Z is {z}, id: {spatId}.'
                      f' Getting grid coordinates {x_ind} and {y_ind}')
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
            packedPolygonsDict = [[], [], [], []]
            blocksCount = np.zeros(4, np.uint32)
            polyVoxelGrid: List = \
                [bytearray(), bytearray(), bytearray(), bytearray()]
            # Step 5. Fill output buffers
            self._make_points_buffer(lodLevel, z_slice,
                                     packedPolygonsDict,
                                     polyVoxelGrid,
                                     blocksCount)

            cellsLodList.append(self._build_cells_btr(
                lodLevel, packedPolygonsDict, polyVoxelGrid))

        return cellsLodList

    def _make_points_buffer(self, lodLevel, zSlice, packedPolygonsDict,
                            polyVoxelGrid,
                            blocksCount):
        polyIdx = [0, 0, 0, 0]

        for polygons in self.grid[zSlice].values():
            polyInVoxel = [0, 0, 0, 0]

            for packSize in range(4):
                polyVoxelGrid[packSize].extend(np.int32(polyIdx[packSize]))

            for curr_poly in polygons:  # type: PolygonSet
                cellId = curr_poly.get_cell_id()
                polyType, packedPolygonsBytes = \
                    curr_poly.get_packed_bytes(lodLevel)

                if polyType >= 0:
                    packedPolygonsDict[polyType].append(
                        packedPolygonsBytes)

                    polyInVoxel[polyType] += 1

                    self.pointersToPolys[cellId][zSlice][0] = polyType + 1
                    if lodLevel == LodLevel.Min:
                        self.pointersToPolys[cellId][zSlice][0] = 1

                    self.pointersToPolys[cellId][zSlice][1] = \
                        blocksCount[polyType]
                    blocksCount[polyType] += 1

            for packSize in range(4):
                polyVoxelGrid[packSize].extend(np.int32(polyInVoxel[packSize]))
                polyIdx[packSize] += polyInVoxel[packSize]

    @staticmethod
    def _build_cells_btr(
            lodLevel, packedPolygonsDict, polyVoxelGrid) -> bytearray:
        output_btr = bytearray()
        # ----  Header ----
        packedPolyBtrDict = {}

        for packSizeType in range(3):
            if lodLevel == LodLevel.Min:
                output_btr.extend(np.uint32(0))
                continue

            packedPolyBtrDict[packSizeType] = \
                b''.join(packedPolygonsDict[packSizeType])
            packedPolySize = PackedStarPolygon.get_bytes_count(
                lodLevel, packSizeType)
            if packedPolySize != 0:
                output_btr.extend(np.uint32(len(packedPolyBtrDict[packSizeType])
                                            / packedPolySize))
            else:
                output_btr.extend(np.uint32(0))

        packedFanPolygons = b''.join(packedPolygonsDict[3])
        packedPolySize = PackedFanPolygon.Bytes_Count[lodLevel.value]
        if packedPolySize != 0:
            output_btr.extend(np.uint32(
                len(packedFanPolygons) / packedPolySize))
        else:
            output_btr.extend(np.uint32(0))

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
        for _, cell in enumerate(self.pointersToPolys):
            zSliceCount = 0
            for zSlice, zSliceData in enumerate(cell):
                if zSliceData[0] != 0:
                    pointersToPolyBtr.extend(np.uint32(zSliceData[1]))
                    pointersToPolyBtr.extend(np.int16(zSliceData[0] - 1))
                    pointersToPolyBtr.extend(np.int16(zSlice))
                    zSliceCount += 1
            cellArray.extend(np.uint32(cellIndex))
            cellArray.extend(np.int32(zSliceCount))
            cellIndex += zSliceCount

        return pointersToPolyBtr, cellArray
