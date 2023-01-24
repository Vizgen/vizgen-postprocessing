from abc import ABC, abstractmethod
import math
from typing import List

import numpy as np
from geopandas import GeoDataFrame, gpd

from vpt.filesystem import vzg_open
from vpt.utils.raw_cell import Feature


class CellsReader(ABC):
    @abstractmethod
    def get_fovs_count(self):
        pass

    @abstractmethod
    def read_fov(self, fov: int) -> List[Feature]:
        pass

    @abstractmethod
    def get_z_planes_count(self) -> int:
        pass

    @abstractmethod
    def get_z_levels(self) -> np.ndarray:
        pass


class CellsGeoReader(CellsReader):
    CELLS_PER_FOV = 10000

    def __init__(self, data: GeoDataFrame):
        data = data.sort_values(by=['EntityID'])
        self._data = data

        polyInCellCont = list(data['EntityID'].value_counts().sort_index())

        prevFovIdx = 0
        fovStartIdxList = [prevFovIdx]
        i = 0
        n = len(polyInCellCont)
        while i < n:
            prevFovIdx += sum(polyInCellCont[i:  min(n, i + self.CELLS_PER_FOV)])
            fovStartIdxList.append(prevFovIdx)
            i += self.CELLS_PER_FOV

        self._fovsStartIdx = fovStartIdxList
        self._nameList = data['EntityID'].unique()

        zLevels = data['ZLevel'].unique()
        zLevels.sort()
        self._zLevelsDiffer = np.diff(zLevels, prepend=0)

        self._zPlanesCount = self._zPlanesCount = 0 if len(data['ZIndex']) == 0 else data['ZIndex'].max() + 1

        self._cellsCount = len(self._nameList)
        self._fovsCount = int(math.ceil(self._cellsCount / self.CELLS_PER_FOV))

    def get_z_levels(self) -> np.ndarray:
        return self._zLevelsDiffer

    def get_fovs_count(self):
        return self._fovsCount

    def read_fov(self, fov: int) -> List[Feature]:
        rawCellsList = []

        polyList = [None] * self._zPlanesCount
        prevEntityIdx = self._data.iloc[self._fovsStartIdx[fov]]['EntityID']
        for rowPolyIdx in range(self._fovsStartIdx[fov], self._fovsStartIdx[fov + 1]):
            rowPoly = self._data.iloc[rowPolyIdx]

            entityIdx = rowPoly['EntityID']
            if prevEntityIdx != entityIdx:
                rawCellsList.append(Feature(str(prevEntityIdx), polyList))
                prevEntityIdx = entityIdx
                polyList = [None] * self._zPlanesCount

            polyGeometry = rowPoly['Geometry']
            if polyGeometry is not None:
                polyList[rowPoly['ZIndex']] = polyGeometry
            continue

        rawCellsList.append(Feature(str(prevEntityIdx), polyList))  # last cell
        return rawCellsList

    def read(self):
        features = []

        for fovIndex in range(self.get_fovs_count()):
            features.extend(self.read_fov(fovIndex))

        return features

    def get_z_planes_count(self) -> int:
        return self._zPlanesCount


def cell_reader_factory(pathToFile) -> CellsReader:
    if pathToFile.endswith('.parquet'):
        with vzg_open(pathToFile, 'rb') as f:
            data: GeoDataFrame = gpd.read_parquet(f)
        return CellsGeoReader(data)

    elif pathToFile.endswith('.geojson'):
        with vzg_open(pathToFile, 'rb') as f:
            data: GeoDataFrame = gpd.read_file(f)
        data = data.rename(columns={'geometry': 'Geometry'})
        return CellsGeoReader(data)

    else:
        raise ValueError("Input geometry has an unsupported file extension")
