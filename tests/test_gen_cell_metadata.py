import os
from argparse import Namespace
from pathlib import Path

import geojson
import numpy as np
import pandas
import pytest
from geojson import Polygon
from shapely import geometry

from tests.temp_dir import TempDir, LocalTempDir
from tests.utils import _copy_between_filesystems
from vpt.derive_cell_metadata.run_derive_cell_metadata import main_derive_cell_metadata
from vpt.filesystem import initialize_filesystem, vzg_open
from vpt.utils.boundaries import Boundaries
from vpt.partition_transcripts.cell_x_gene import cell_by_gene_matrix
from vpt.derive_cell_metadata.cell_metadata import create_metadata_table
from vpt.utils.cellsreader import cell_reader_factory, CellsReader

# todo:
TEST_DATA_ROOT = (Path(__file__).parent / 'data').resolve()

gj_file = TEST_DATA_ROOT / 'sample.geojson'
transcripts_file = TEST_DATA_ROOT / 'sample_trans.csv'
matrix_file = TEST_DATA_ROOT / 'uniform_matrix.csv'

initialize_filesystem()


def test_create_metatable():
    cellsReader = cell_reader_factory(str(gj_file))
    tbl = create_metadata_table(Boundaries(cellsReader), cellsReader.get_z_levels())
    assert len(tbl.index) == 10


def test_gen_cell_x_gene():
    cellsReader: CellsReader = cell_reader_factory(str(gj_file))
    bnds = Boundaries(cellsReader)
    with vzg_open(str(transcripts_file), 'r') as f:
        transcripts = pandas.read_csv(f, chunksize=10000)
        pd = cell_by_gene_matrix(bnds, transcripts)
    vals = pd.values.tolist()

    assert np.max(np.abs(np.array(vals[:3]) - np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 1, 0, 0]]))) < 1e-8

    assert sum([sum(x) for x in vals[3:]]) == 0


@pytest.mark.parametrize('temp_dir', [LocalTempDir()], ids=str)
def test_func_derive_cell_metadata(temp_dir: TempDir):
    path = temp_dir.get_temp_path()
    sep = temp_dir.get_sep()
    fakesNamespaceArgs = Namespace(
        input_boundaries=sep.join([path, 'sample.geojson']),
        output_metadata=sep.join([path, 'output', 'test_cell_metadata.csv']),
        input_entity_by_gene=None,
        overwrite=True
    )
    try:
        _copy_between_filesystems(str(gj_file), fakesNamespaceArgs.input_boundaries)

        zDepth = 1.5
        main_derive_cell_metadata(fakesNamespaceArgs)

        # checking
        with vzg_open(fakesNamespaceArgs.output_metadata, 'r') as f:
            cellMetadataDf = pandas.read_csv(f)
        with vzg_open(fakesNamespaceArgs.input_boundaries, 'r') as f:
            features = geojson.load(f)['features']

        cellsCount = len(features)
        for featureIdx in range(cellsCount):
            poly: Polygon = geometry.shape(features[featureIdx]['Geometry'])

            assert poly.area * zDepth == cellMetadataDf['volume'][featureIdx]
            assert poly.centroid.x == cellMetadataDf['center_x'][featureIdx]
            assert poly.centroid.y == cellMetadataDf['center_y'][featureIdx]

            assert poly.bounds[0] == cellMetadataDf['min_x'][featureIdx]
            assert poly.bounds[1] == cellMetadataDf['min_y'][featureIdx]
            assert poly.bounds[2] == cellMetadataDf['max_x'][featureIdx]
            assert poly.bounds[3] == cellMetadataDf['max_y'][featureIdx]

        # deleting temporary file
        if os.path.exists(fakesNamespaceArgs.output_metadata):
            os.remove(fakesNamespaceArgs.output_metadata)
    finally:
        temp_dir.clear_dir()
