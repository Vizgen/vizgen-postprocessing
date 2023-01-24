from copy import deepcopy
from typing import List
import numpy as np

from vpt.update_vzg.assemble.expression_matrix import GeneExprMatrix, ExpressionMetric


def create_bytearray(array_l, array_type=np.float32) -> bytearray:
    output_btr = bytearray()
    for element in array_l:
        output_btr.extend(array_type(element))

    return output_btr


class CellColoring:
    def __init__(self, matrix: GeneExprMatrix):
        self._matrix = matrix
        self._normalized_matrix = None
        self._cellsMetricsList: List = []

        self._metricExtr = []
        for i in range(ExpressionMetric.ItemsCount.value):
            self._cellsMetricsList.append(np.zeros(matrix.lines_cells, np.float32))
            self._metricExtr.append(np.zeros(2, np.float32))
            self._metricExtr[i][0] = float('inf')
            self._metricExtr[i][1] = float('-inf')

        self._outputNameBtrDict: dict = {}

    def _make_cell_lists(self):
        data = self._matrix.data
        sigma_genes = []
        for genes_column in self._matrix.data.T:
            sigma_genes.append(np.std(genes_column))

        self._metricExtr[ExpressionMetric.Count.value][0] = data.min()
        self._metricExtr[ExpressionMetric.Count.value][1] = data.max()

        for i, row_transcripts in enumerate(data):
            self._cellsMetricsList[ExpressionMetric.Count.value][i] = np.sum(row_transcripts)

        self._normalized_matrix: GeneExprMatrix = deepcopy(self._matrix)
        self._normalized_matrix.change_matrix_data_from_origin(ExpressionMetric.Normalized)
        normalized_data = self._normalized_matrix.data
        normalized_sigma_genes = []

        self._metricExtr[ExpressionMetric.Normalized.value][0] = normalized_data.min()
        self._metricExtr[ExpressionMetric.Normalized.value][1] = normalized_data.max()

        for genes_column in self._normalized_matrix.data.T:
            normalized_sigma_genes.append(np.std(genes_column))

        for i, row_transcripts in enumerate(normalized_data):
            self._cellsMetricsList[ExpressionMetric.Normalized.value][i] = np.sum(row_transcripts)

        self._outputNameBtrDict: dict = {
            'genes_mean': create_bytearray(self._matrix.average_genes),
            'genes_sigma': create_bytearray(sigma_genes),
            'normalized_genes_mean': create_bytearray(
                self._normalized_matrix.average_genes),
            'normalized_genes_sigma': create_bytearray(normalized_sigma_genes)
        }

    def calculate_coloring_arrays(self):
        file_names = {
            ExpressionMetric.Count: 'cell_count',
            ExpressionMetric.Normalized: 'cell_normalized',
        }

        self._make_cell_lists()
        statisticsVariablesBtr = bytearray()

        for metric in file_names.keys():
            cell_metric_btr = bytearray()  # t[i]
            for i in range(self._matrix.lines_cells):
                cell_metric_btr.extend(np.float32(self._cellsMetricsList[metric.value][i]))

            statisticsVariablesBtr.extend(np.float32(np.min(self._cellsMetricsList[metric.value])))
            statisticsVariablesBtr.extend(np.float32(np.max(self._cellsMetricsList[metric.value])))
            self._outputNameBtrDict[file_names[metric]] = cell_metric_btr

        for metric in file_names.keys():
            statisticsVariablesBtr.extend(self._metricExtr[metric.value][0])
            statisticsVariablesBtr.extend(self._metricExtr[metric.value][1])

        self._outputNameBtrDict['statistics_variables'] = statisticsVariablesBtr
        return self._outputNameBtrDict
