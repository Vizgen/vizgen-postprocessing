from enum import Enum
from typing import Tuple

import numpy as np
import pandas

from vpt.update_vzg.byte_utils import extend_with_u32
from vpt.update_vzg.cell_metadata import CellMetadata


class ExpressionMetric(Enum):
    Count = 0  # Genes Sum
    Normalized = 1  # divided on cell volume
    ItemsCount = 2


class GeneExprMatrix:
    """
        Original expression matrix looks like (schema 1):
            Gene0   |   Gene1   |   Gene2   |   Gene3   |   Gene4  |   Gene5   |   Gene6
    Cell0|    0     |     5     |     0     |     0     |     3    |     0     |    0
    Cell1|    2     |     1     |     0     |     0     |     0    |     5     |    0
    Cell2|    0     |     0     |     4     |     3     |     0    |     8     |    7
    """

    def __init__(self, exprMatrix: pandas.DataFrame, cellMetadata: CellMetadata):
        self._cellMetaData = cellMetadata
        self.data = np.zeros(0)
        self.columns_genes = 0
        self.lines_cells = 0

        self.average_sum = None  # μ
        self.std = None  # σ
        self.average_genes = None

        self._load_matrix_data(exprMatrix)

    def _calculate_statistic_variables(self):
        self.average_sum = np.mean(self.data)  # μ
        self.std = np.std(self.data)  # σ
        self.average_genes = np.array(self.columns_genes)

        self.average_genes = np.mean(self.data, 0)

    def _load_matrix_data(self, exprMatrix):
        exprMatrix = exprMatrix.sort_index()
        self.data = exprMatrix.to_numpy()
        self.lines_cells = len(self.data)
        self.columns_genes = len(self.data[0])

        self._calculate_statistic_variables()

    def change_matrix_data_from_origin(self, creation: ExpressionMetric):
        if creation == ExpressionMetric.Normalized:
            self._normalize_data_by_cell_volume(self.data)
            self._calculate_statistic_variables()

    def _normalize_data_by_cell_volume(self, origin_data):
        volume_np = self._cellMetaData.get_volume_array()

        self.lines_cells, self.columns_genes = len(origin_data), len(origin_data[0])

        self.data = np.zeros((self.lines_cells, self.columns_genes), np.float32)
        for cell_number, cell_row in enumerate(self.data):
            cell_volume = volume_np[cell_number]
            self.data[cell_number] = origin_data[cell_number] / cell_volume

    def generate_sparse_gene_expr_matrix_data(self) -> Tuple[bytearray, bytearray]:
        """
            Original matrix is rather sparse, so we need to store data efficiently, this function generate 3 arrays,
        that determine information that we use from original matrix (example from scheme 1):
            1. An array of the number of gene transcripts in cells and their gene numbers :
            |   5   |   3   |   2   |   1   |   5   |   4   |   3   |   8   |   7   |
            |   1   |   4   |   0   |   1   |   5   |   2   |   3   |   5   |   6   |
            2. Array of cell indices:
            |   0   |   2   |   5   |
            3. An array of maximum numbers of gene transcripts in cells:
            |   2   |   5   |   4   |   3   |   3   |   8   |   7   |
        """
        transcripts_gene_number_btr = bytearray()
        transcripts_gene_indices_btr = bytearray()
        genesCountList = []
        genesArrayList = []
        geneIndexList = []

        writen_element_id = 0
        for cell_line in range(self.lines_cells):
            first_gene = True
            genesCountList.append(str(cell_line) + " " + str(np.sum(self.data[cell_line])) + "\n")
            for gene_number in range(self.columns_genes):
                transcripts_count = self.data[cell_line][gene_number]
                if transcripts_count != 0:
                    if first_gene:
                        extend_with_u32(transcripts_gene_indices_btr, writen_element_id)
                        first_gene = False
                        geneIndexList.append(str(writen_element_id) + "\n")

                    extend_with_u32(transcripts_gene_number_btr, transcripts_count)
                    extend_with_u32(transcripts_gene_number_btr, gene_number)
                    genesArrayList.append(str(transcripts_count) + " " + str(gene_number) + "\n")
                    writen_element_id += 1

            if first_gene:
                extend_with_u32(transcripts_gene_indices_btr, writen_element_id)
                geneIndexList.append(str(writen_element_id) + "\n")

        return transcripts_gene_number_btr, transcripts_gene_indices_btr

    def generate_sparse_cell_expr_matrix_data(self):
        """
        Function makes 2 arrays from original expression matrix, unlike generate_sparse_cell_expr_matrix_data it is made
        along the Y (cell) axis.
        1. Non-zero matrix elements are ordered in the array by genes :
        |   2   |   5   |   1   |   4   |   3   |   3   |   5   |   8   |   7   |
        |   1   |   0   |   1   |   2   |   2   |   0   |   1   |   2   |   2   |
        2. Array of indices:
        |   0   |   1   |   3   |   4   |   5   |   6   |   8   |
        """
        transcripts_cell_number_btr = bytearray()
        transcripts_cell_indices_btr = bytearray()

        writen_element_id = 0
        for gene_column in range(self.columns_genes):
            first_cell = True
            for cell_line in range(self.lines_cells):
                transcripts_count = self.data[cell_line][gene_column]
                if transcripts_count != 0:
                    if first_cell:
                        transcripts_cell_indices_btr.extend(np.uint32(writen_element_id))
                        first_cell = False

                    transcripts_cell_number_btr.extend(np.uint32(transcripts_count))
                    transcripts_cell_number_btr.extend(np.uint32(cell_line))
                    writen_element_id += 1

            if first_cell:
                transcripts_cell_indices_btr.extend(np.uint32(writen_element_id))

        return transcripts_cell_number_btr, transcripts_cell_indices_btr
