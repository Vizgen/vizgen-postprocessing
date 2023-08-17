import math
from typing import List

import geopandas as gpd
import numpy as np
from vpt_core.io.vzgfs import io_with_retries

from vpt.utils.cellsreader.base_reader import CellsReader
from vpt.utils.raw_cell import Feature


class CellsGeoReader(CellsReader):
    def __init__(self, data_path: str):
        data: gpd.GeoDataFrame = io_with_retries(data_path, "rb", gpd.read_file)
        data = data.rename(columns={"geometry": "Geometry"})

        self._initialize_with_data(data)

    def _initialize_with_data(self, data: gpd.GeoDataFrame):
        data = data.sort_values(by=["EntityID"])
        self._data = data

        poly_in_cell_count = list(data["EntityID"].value_counts().sort_index())

        prev_fov_idx = 0
        fov_start_idx = [prev_fov_idx]
        i = 0
        n = len(poly_in_cell_count)
        while i < n:
            prev_fov_idx += sum(poly_in_cell_count[i : min(n, i + self.CELLS_PER_FOV)])
            fov_start_idx.append(prev_fov_idx)
            i += self.CELLS_PER_FOV

        self._fovs_start_idx = fov_start_idx
        self._nameList = data["EntityID"].unique()

        z_levels = data["ZLevel"].unique()
        z_levels.sort()
        self._z_levels_diff = np.diff(z_levels, prepend=0)

        self._zPlanesCount = 0 if len(data["ZIndex"]) == 0 else data["ZIndex"].max() + 1

        self._cells_count = len(self._nameList)
        self._fovs_count = int(math.ceil(self._cells_count / self.CELLS_PER_FOV))

    def get_z_depth_per_level(self) -> np.ndarray:
        return self._z_levels_diff

    def get_fovs_count(self):
        return self._fovs_count

    def read_fov(self, fov: int) -> List[Feature]:
        raw_cells = []

        cell_polys = [None] * self._zPlanesCount
        prev_entity_idx = self._data.iloc[self._fovs_start_idx[fov]]["EntityID"]
        for row_poly_idx in range(self._fovs_start_idx[fov], self._fovs_start_idx[fov + 1]):
            row_poly = self._data.iloc[row_poly_idx]

            entity_idx = row_poly["EntityID"]
            if prev_entity_idx != entity_idx:
                raw_cells.append(Feature(str(prev_entity_idx), cell_polys))
                prev_entity_idx = entity_idx
                cell_polys = [None] * self._zPlanesCount

            poly_geometry = row_poly["Geometry"]
            if poly_geometry is not None:
                cell_polys[row_poly["ZIndex"]] = poly_geometry
            continue

        raw_cells.append(Feature(str(prev_entity_idx), cell_polys))  # last cell
        return raw_cells

    def read(self):
        features = []

        for fovIndex in range(self.get_fovs_count()):
            features.extend(self.read_fov(fovIndex))

        return features

    def get_z_planes_count(self) -> int:
        return self._zPlanesCount

    def _set_cells_per_fov(self, cells_per_fov: int):
        self.CELLS_PER_FOV = cells_per_fov
        self._initialize_with_data(self._data)
