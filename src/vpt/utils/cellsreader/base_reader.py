from abc import ABC, abstractmethod
from typing import List

import numpy as np

from vpt.utils.raw_cell import Feature


class CellsReader(ABC):
    CELLS_PER_FOV = 10000

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
    def get_z_depth_per_level(self) -> np.ndarray:
        pass

    @abstractmethod
    def _set_cells_per_fov(self, cells_per_fov: int):
        pass
