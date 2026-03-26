import numpy as np

from vpt_segmentation_packing.celltransfer import CellTransfer
from vpt_segmentation_packing.data import Feature, WebPolygonManager


def preprocess_cells(
    featureList: list[Feature],
    texSize: tuple[int, int],
    transformationMatrix: np.ndarray,
    cells_version: str = "5",
) -> list[WebPolygonManager]:
    assert cells_version in ["5"], f"Cells version {cells_version} is not supported by the current package version"
    cellTransfer = CellTransfer(texSize[0], texSize[1], transformationMatrix)
    return cellTransfer.process_cells(featureList)
