import argparse
import json
import os
import tempfile
from unittest import mock

import numpy as np
import pandas as pd
from vpt_segmentation_packing.unpack import load_lod

from tests.vpt import TEST_DATA_ROOT
from vpt.derive_cell_metadata.cell_metadata import create_input_metadata
from vpt.update_vzg.vzg2.run_update import preprocess_and_pack_feature_set, preprocess_feature_set
from vpt.utils.input_utils import read_geodataframe


def _create_input_entity_by_gene(workdir, input_boundaries, name):
    num_genes = 50

    boundaries = read_geodataframe(input_boundaries)
    entity_by_gene = pd.DataFrame(
        np.random.randint(0, 100, size=(len(boundaries), num_genes)),
        columns=[f"Gene{i}" for i in range(num_genes)],
        index=boundaries["EntityID"],
    )

    output_path = os.path.join(workdir, f"{name}_by_gene.csv")
    entity_by_gene.to_csv(output_path)

    return output_path


@mock.patch("vpt.update_vzg.vzg2.run_update.cell_reader_factory")
@mock.patch("vpt.update_vzg.vzg2.run_update.preprocess_cells")
def test_preprocess_feature_set(mock_preprocess_cells, mock_cell_reader_factory):
    total_tasks = 5
    fov_count = 100

    mock_reader = mock.MagicMock()
    mock_reader.get_fovs_count = mock.Mock(return_value=fov_count)

    mock_cell_reader_factory.return_value = mock_reader

    for i in range(total_tasks):
        preprocess_feature_set(
            argparse.Namespace(
                input_boundaries="path",
                task_id=i,
                total_tasks=total_tasks,
                tex_size=mock.MagicMock(),
                transform_matrix=mock.MagicMock(),
            )
        )

    assert sorted(mock_reader.read_fov.call_args_list) == [mock.call(i) for i in range(fov_count)]
    assert mock_preprocess_cells.call_count == mock_reader.read_fov.call_count == fov_count


@mock.patch("vpt.utils.cellsreader.parquet_reader.CellsParquetReader.CELLS_PER_FOV", 150)
def test_preprocess_and_pack_feature_set():
    mock_context = mock.Mock()
    mock_context.get_workers_count = mock.Mock(return_value=5)

    with mock.patch(
        "vpt.update_vzg.vzg2.run_update.current_context", return_value=mock_context
    ), tempfile.TemporaryDirectory() as td:
        input_boundaries = str(TEST_DATA_ROOT / "cells_cellpose_row_groups.parquet")
        input_metadata = create_input_metadata(td, input_boundaries, "cells")
        input_entity_by_gene = _create_input_entity_by_gene(td, input_boundaries, "cells")

        tex_size = 5_000, 5_000
        transform_matrix = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        num_z_planes = 7

        feature_set_path = preprocess_and_pack_feature_set(
            td,
            input_metadata,
            input_boundaries,
            input_entity_by_gene,
            tex_size,
            transform_matrix,
            num_z_planes,
            "cells",
        )

        # Make sure the packed cell count is approximately equal to the number of input cells in each lod
        with open(os.path.join(td, feature_set_path, "manifest_cells.json"), "r") as f:
            cells_manifest = json.load(f)

        x1, y1, _ = np.linalg.inv(transform_matrix).dot([0, 0, 1])
        x2, y2, _ = np.linalg.inv(transform_matrix).dot([tex_size[0], tex_size[1], 1])

        manifest = {
            "bbox_microns": [x1, y1, x2, y2],
            "mosaic_width_pixels": tex_size[0],
            "mosaic_height_pixels": tex_size[1],
        }

        boundaries = read_geodataframe(input_boundaries)

        for lod_index in range(len(cells_manifest["tiles"])):
            polygons = []
            for z_plane_index in range(num_z_planes):
                polygons.extend(
                    load_lod(lod_index, z_plane_index, manifest, cells_manifest, os.path.join(td, feature_set_path))
                )
            assert len(polygons) >= boundaries.shape[0] * 0.95
