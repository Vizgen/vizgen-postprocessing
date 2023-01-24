import os
from typing import Optional

import pandas

from vpt.update_vzg.assemble.cell_coloring import CellColoring
from vpt.update_vzg.assemble.expression_matrix import GeneExprMatrix
from vpt.filesystem import vzg_open
from vpt.update_vzg.cell_metadata import CellMetadata
from vpt.utils.general_data import write_file


def run_dataset_assembling(exprMatrixPath: str, outputDatasetPath: str,
                           cellMetadata: CellMetadata,
                           genes: Optional[list[str]] = None):
    with vzg_open(exprMatrixPath, 'r') as f:
        exprMatrixDF: pandas.DataFrame = pandas.read_csv(f, index_col=0)

    # Sort cell by gene matrix by EntityID if it isn't already sorted
    exprMatrixDF = exprMatrixDF.sort_index()

    if genes:
        exprMatrixDF = exprMatrixDF.assign(**{g: 0 for g in set(genes) - set(exprMatrixDF.columns)})
        exprMatrixDF = exprMatrixDF.reindex(columns=genes)

    exprMatrix = GeneExprMatrix(exprMatrixDF, cellMetadata)

    print('Start calculating expression matrices')
    exprMatrixFolder = os.path.join('assemble', 'expression_matrix')
    transcripts_gene_number_btr, transcripts_gene_indices_btr =\
        exprMatrix.generate_sparse_gene_expr_matrix_data()
    write_file(outputDatasetPath, transcripts_gene_number_btr,
               'sparse_gene_expr_matrix.bin', exprMatrixFolder)
    write_file(outputDatasetPath, transcripts_gene_indices_btr,
               'expr_matrix_gene_indices.bin', exprMatrixFolder)

    transcripts_cell_number_btr, transcripts_cell_indices_btr =\
        exprMatrix.generate_sparse_cell_expr_matrix_data()
    write_file(outputDatasetPath, transcripts_cell_number_btr,
               'sparse_cell_expr_matrix.bin', exprMatrixFolder)
    write_file(outputDatasetPath, transcripts_cell_indices_btr,
               'expr_matrix_cell_indices.bin', exprMatrixFolder)

    print('Start calculating coloring arrays')
    cellColoring = CellColoring(exprMatrix)
    nameBtrDict = cellColoring.calculate_coloring_arrays()

    cellColoringFolder = os.path.join('assemble', 'coloring_arrays')
    for fileName, resultBtr in nameBtrDict.items():
        write_file(outputDatasetPath, resultBtr, f'{fileName}.bin', cellColoringFolder)

    print('Finish calculating')
