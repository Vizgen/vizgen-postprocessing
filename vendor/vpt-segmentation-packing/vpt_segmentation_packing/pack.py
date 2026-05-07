import json
import os
from typing import Optional, Union

import numpy as np
import pandas as pd

from vpt_segmentation_packing.cellgenerator import WebCellGenerator
from vpt_segmentation_packing.data import WebLodLevel, WebPolygonManager
from vpt_segmentation_packing.util.io import save_parquet_analysis_result
from vpt_segmentation_packing.util.vizwebmanifest import VizWebManifestGenerator

LOD_PATH = {
    WebLodLevel.LOD0: "Lod0",
    WebLodLevel.LOD1: "Lod1",
    WebLodLevel.LOD2: "Lod2",
}


def _save_expression_data(exprMatrixDf: pd.DataFrame, outputDir: Union[str, os.PathLike]) -> None:
    # The visualizers expect the index to be sorted, the index name to be None and the data type to float32
    exprMatrixDf = exprMatrixDf.sort_index().set_index(exprMatrixDf.index.rename(None), drop=True).astype(np.float32)

    cellByGeneDir = os.path.join(outputDir, "cell_by_gene")
    os.makedirs(cellByGeneDir, exist_ok=True)

    save_parquet_analysis_result(exprMatrixDf, "cell_by_gene", cellByGeneDir)

    cellByIndGeneDir = os.path.join(outputDir, "cell_by_ind_genes")
    os.makedirs(cellByIndGeneDir, exist_ok=True)

    for column in exprMatrixDf.columns:
        save_parquet_analysis_result(exprMatrixDf[column].to_frame(), column, cellByIndGeneDir, index=False)

    allGenes = exprMatrixDf.sum(axis=1).to_frame(name="genes_sum")
    save_parquet_analysis_result(allGenes, "all_genes", cellByIndGeneDir, index=False)

    countGenes = [np.mean(exprMatrixDf[gene]) for gene in exprMatrixDf.columns]
    sigmaGenes = [np.std(exprMatrixDf[gene]) for gene in exprMatrixDf.columns]

    with open(os.path.join(outputDir, "genes_sigma.bin"), "wb") as f:
        f.write(np.asarray(sigmaGenes, dtype=np.float32).tobytes())

    with open(os.path.join(outputDir, "genes_mean.bin"), "wb") as f:
        f.write(np.asarray(countGenes, dtype=np.float32).tobytes())


def _save_cell_metadata(cellMetadata: pd.DataFrame, outputDir: Union[str, os.PathLike]) -> None:
    save_parquet_analysis_result(
        cellMetadata.index.to_frame(name="cell_indices"), "cells_indices", outputDir, index=False
    )
    save_parquet_analysis_result(
        cellMetadata.loc[:, ["center_x", "center_y"]].astype(np.float32), "cells_centers", outputDir, index=False
    )
    save_parquet_analysis_result(
        cellMetadata.loc[:, ["volume"]].astype(np.float32), "cells_volume", outputDir, index=False
    )


def _pack_lod(cellsTiledBtrList: list[bytearray], outputDir: Union[str, os.PathLike]) -> None:
    os.makedirs(outputDir, exist_ok=True)

    for i, cellsTiledBtr in enumerate(cellsTiledBtrList):
        tilePath = os.path.join(outputDir, f"tile{i}.bin")

        with open(tilePath, "wb") as f:
            f.write(cellsTiledBtr)


def pack_cells(
    polyList: list[WebPolygonManager],
    cellsDir: Union[str, os.PathLike],
    zPlaneCount: int,
    texSize: tuple[int, int],
    transformMatrix: np.ndarray,
    cellMetadata: pd.DataFrame,
    expressionMatrix: Optional[pd.DataFrame] = None,
    cells_version: str = "5",
) -> None:
    """
    Creates all required vzg2 cell files in the given directory
    from the WebPolygonManager objects that are output by vpt_segmentation_packing.cells.preprocess_cells
    """
    assert cells_version in ["5"], f"Cells version {cells_version} is not supported by the current package version"
    assert not os.path.exists(cellsDir) or os.listdir(cellsDir) == [], f"Directory is not empty: {cellsDir}"

    allIndices = sorted(cellMetadata.index)

    cellGenerator = WebCellGenerator(zPlaneCount)
    cellGenerator.set_data(polyList, texSize[0], texSize[1], transformMatrix, allIndices)

    for zSlice in range(zPlaneCount):
        zPlaneDir = os.path.join(cellsDir, f"z-plane{zSlice}")

        for lod_level in [WebLodLevel.LOD0, WebLodLevel.LOD1, WebLodLevel.LOD2]:
            _pack_lod(
                cellGenerator.get_cells_by_lod(lod_level, zSlice),
                os.path.join(zPlaneDir, LOD_PATH[lod_level]),
            )

    _save_cell_metadata(cellMetadata, cellsDir)

    if expressionMatrix is not None:
        _save_expression_data(expressionMatrix, cellsDir)

    geneNamesArray = cellMetadata.index.tolist()

    with open(os.path.join(cellsDir, "cells_names_array.json"), "w") as f:
        json.dump(geneNamesArray, f)

    cellsManifest = VizWebManifestGenerator("cells", version=cells_version)
    cellsManifest.add_parameter("tiles", cellGenerator.get_grid_size())

    with open(os.path.join(cellsDir, "manifest_cells.json"), "w") as f:
        json.dump(cellsManifest.to_dict(), f)
