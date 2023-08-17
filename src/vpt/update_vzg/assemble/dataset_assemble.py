import os
from typing import Dict, Optional

import pandas
from vpt_core import log
from vpt_core.io.vzgfs import io_with_retries

from vpt.update_vzg.assemble.cell_coloring import CellColoring
from vpt.update_vzg.assemble.expression_matrix import GeneExprMatrix
from vpt.update_vzg.cell_metadata import CellMetadata
from vpt.utils.general_data import write_file


def identify_sequential(genes: list[Dict], channels: list[str]) -> list[str]:
    sequential_genes = []
    following_blank = False
    for g in genes:
        if g["name"].lower().find("blank") >= 0:
            following_blank = True
        elif following_blank and g["count"] == 0 and g["name"] in channels:
            sequential_genes.append(g["name"])
    return sequential_genes


def run_dataset_assembling(
    exprMatrixPath: str, outputDatasetPath: str, cellMetadata: CellMetadata, genes: Optional[list[str]] = None
):
    exprMatrixDF: pandas.DataFrame = io_with_retries(exprMatrixPath, "r", lambda f: pandas.read_csv(f, index_col=0))

    # Sort cell by gene matrix by EntityID if it isn't already sorted
    exprMatrixDF = exprMatrixDF.sort_index()

    if genes:
        exprMatrixDF = exprMatrixDF.assign(**{g: 0 for g in set(genes) - set(exprMatrixDF.columns)})
        exprMatrixDF = exprMatrixDF.reindex(columns=genes)

    exprMatrix = GeneExprMatrix(exprMatrixDF, cellMetadata)

    log.info("Start calculating expression matrices")
    exprMatrixFolder = os.path.join("assemble", "expression_matrix")
    transcripts_gene_number_btr, transcripts_gene_indices_btr = exprMatrix.generate_sparse_gene_expr_matrix_data()
    write_file(outputDatasetPath, transcripts_gene_number_btr, "sparse_gene_expr_matrix.bin", exprMatrixFolder)
    write_file(outputDatasetPath, transcripts_gene_indices_btr, "expr_matrix_gene_indices.bin", exprMatrixFolder)

    transcripts_cell_number_btr, transcripts_cell_indices_btr = exprMatrix.generate_sparse_cell_expr_matrix_data()
    write_file(outputDatasetPath, transcripts_cell_number_btr, "sparse_cell_expr_matrix.bin", exprMatrixFolder)
    write_file(outputDatasetPath, transcripts_cell_indices_btr, "expr_matrix_cell_indices.bin", exprMatrixFolder)

    log.info("Start calculating coloring arrays")
    cellColoring = CellColoring(exprMatrix)
    nameBtrDict = cellColoring.calculate_coloring_arrays()

    cellColoringFolder = os.path.join("assemble", "coloring_arrays")
    for fileName, resultBtr in nameBtrDict.items():
        write_file(outputDatasetPath, resultBtr, f"{fileName}.bin", cellColoringFolder)

    log.info("Finish calculating")
