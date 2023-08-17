import io
from typing import List

import numpy as np
from pyarrow.parquet import ParquetFile
from shapely import wkb
from vpt_core.io.vzgfs import vzg_open, retrying_attempts
from vpt_core.segmentation.seg_result import SegmentationResult

from vpt.utils.cellsreader.base_reader import CellsReader
from vpt.utils.raw_cell import Feature


class CellsParquetReader(CellsReader):
    pq_data: ParquetFile
    fd: io.TextIOWrapper

    _fovs_count: int
    _fov_size: int
    _z_planes: np.ndarray
    _z_levels_diff: np.ndarray
    _groups_start: List[int]

    def __init__(self, data_path: str):
        for attempt in retrying_attempts():
            with attempt:
                self.fd = vzg_open(data_path, "rb")
                self.pq_data = ParquetFile(self.fd)
                self._z_planes = np.unique(self.pq_data.read(columns=[SegmentationResult.z_index_field]))

                z_levels = np.unique(self.pq_data.read(columns=["ZLevel"]))
                z_levels.sort()
                self._z_levels_diff = np.diff(z_levels, prepend=0)
        self._fov_size = self.CELLS_PER_FOV * self.get_z_planes_count()
        self._fovs_count = 0 if self._fov_size == 0 else int(np.ceil(self.pq_data.metadata.num_rows / self._fov_size))

        self._groups_start = [0]
        for i in range(self.pq_data.metadata.num_row_groups):
            self._groups_start.append(self._groups_start[-1] + self.pq_data.metadata.row_group(i).num_rows)

    def get_fovs_count(self):
        return self._fovs_count

    def read_fov(self, fov: int) -> List[Feature]:
        result = []
        start_row = self._fov_size * fov
        end_row = self._fov_size * (fov + 1)
        for i in range(len(self._groups_start) - 1):
            if self._groups_start[i + 1] <= start_row or self._groups_start[i] >= end_row:
                continue
            group_size = self._groups_start[i + 1] - self._groups_start[i]
            result.extend(
                self.read_row_group_fov(
                    i, max(0, start_row - self._groups_start[i]), min(group_size, end_row - self._groups_start[i])
                )
            )

        return result

    def read_row_group_fov(self, group_i, start, end) -> List[Feature]:
        result = []
        for attempt in retrying_attempts():
            with attempt:
                group_data = self.pq_data.read_row_group(group_i).to_pandas()
        group_data = group_data.sort_values(by=[SegmentationResult.cell_id_field])

        geometry_col = SegmentationResult.geometry_field
        group_data[geometry_col] = group_data[geometry_col].apply(wkb.loads)

        entity_id_col = group_data.columns.get_loc(SegmentationResult.cell_id_field)

        # shift fov's rows to the left until it contains whole cells at the edges
        while start > 0 and group_data.iat[start - 1, entity_id_col] == group_data.iat[start, entity_id_col]:
            start -= 1
        if end < len(group_data):
            while end > start - 1 and group_data.iat[end - 1, entity_id_col] == group_data.iat[end, entity_id_col]:
                end -= 1

        for cell_id, gdf in group_data[start:end].groupby(SegmentationResult.cell_id_field):
            polys = [None] * self.get_z_planes_count()
            for i in gdf.index:
                polys[gdf[SegmentationResult.z_index_field][i]] = gdf[geometry_col][i]
            result.append(Feature(str(cell_id), polys))
        return result

    def get_z_planes_count(self) -> int:
        return 0 if len(self._z_planes) == 0 else max(self._z_planes) + 1

    def get_z_depth_per_level(self) -> np.ndarray:
        return self._z_levels_diff

    def _set_cells_per_fov(self, cells_per_fov: int):
        self.CELLS_PER_FOV = cells_per_fov
        self._fov_size = self.CELLS_PER_FOV * self.get_z_planes_count()
        self._fovs_count = int(np.ceil(self.pq_data.metadata.num_rows / self._fov_size))

    def __del__(self):
        self.fd.close()
