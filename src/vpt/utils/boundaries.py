import warnings

from shapely.errors import ShapelyDeprecationWarning

from vpt.utils.cellsreader import CellsReader


class Boundaries:
    def __init__(self, cellsReader: CellsReader):
        warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)
        self.cellsReader = cellsReader

    def get_z_planes_count(self) -> int:
        return self.cellsReader.get_z_planes_count()

    @property
    def features(self):
        for fovIdx in range(self.cellsReader.get_fovs_count()):
            for feature in self.cellsReader.read_fov(fovIdx):
                yield feature
