import os
import tempfile
from argparse import Namespace

import geopandas as gpd
import numpy as np
import pandas
import pytest
from shapely import geometry
from shapely.geometry import Polygon
from vpt_core.io.output_tools import save_geodataframe
from vpt_core.io.vzgfs import initialize_filesystem, vzg_open, retrying_attempts, io_with_retries
from vpt_core.segmentation.seg_result import SegmentationResult
from vpt_core.utils.copy_utils import _copy_between_filesystems

from tests.vpt import TEST_DATA_ROOT
from tests.vpt.temp_dir import LocalTempDir, TempDir
from vpt.derive_cell_metadata.cell_metadata import create_metadata_table
from vpt.derive_cell_metadata.run_derive_cell_metadata import main_derive_cell_metadata
from vpt.partition_transcripts.cell_x_gene import cell_by_gene_matrix
from vpt.utils.boundaries import Boundaries
from vpt.utils.cellsreader import CellsReader, cell_reader_factory
from vpt.utils.cellsreader.geo_reader import CellsGeoReader
from vpt.utils.cellsreader.parquet_reader import CellsParquetReader

DATA_ROOT = TEST_DATA_ROOT / "test_gen_cell_metadata"
gj_file = DATA_ROOT / "sample.geojson"
transcripts_file = DATA_ROOT / "sample_trans.csv"
matrix_file = DATA_ROOT / "uniform_matrix.csv"

initialize_filesystem()


def test_create_metatable():
    cellsReader = cell_reader_factory(str(gj_file))
    tbl = create_metadata_table(Boundaries(cellsReader), cellsReader.get_z_depth_per_level())
    assert len(tbl.index) == 10


def test_metadata_solidity():
    cellsReader = cell_reader_factory(str(DATA_ROOT / "sample2.geojson"))
    tbl = create_metadata_table(Boundaries(cellsReader), cellsReader.get_z_depth_per_level())
    assert all(tbl["solidity"] > 0) and all(tbl["solidity"] <= 1)


def test_gen_cell_x_gene():
    cellsReader: CellsReader = cell_reader_factory(str(gj_file))
    bnds = Boundaries(cellsReader)
    for attempt in retrying_attempts():
        with attempt, vzg_open(str(transcripts_file), "r") as f:
            transcripts = pandas.read_csv(f, chunksize=10000)
            pd = cell_by_gene_matrix(bnds, transcripts)
    vals = pd.values.tolist()

    assert np.max(np.abs(np.array(vals[:3]) - np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 1, 0, 0]]))) < 1e-8

    assert sum([sum(x) for x in vals[3:]]) == 0


@pytest.mark.parametrize("temp_dir", [LocalTempDir()], ids=str)
def test_func_derive_cell_metadata(temp_dir: TempDir):
    path = temp_dir.get_temp_path()
    sep = temp_dir.get_sep()
    fakesNamespaceArgs = Namespace(
        input_boundaries=sep.join([path, "sample.geojson"]),
        output_metadata=sep.join([path, "output", "test_cell_metadata.csv"]),
        input_entity_by_gene=None,
        overwrite=True,
    )
    try:
        _copy_between_filesystems(str(gj_file), fakesNamespaceArgs.input_boundaries)

        zDepth = 1.5
        main_derive_cell_metadata(fakesNamespaceArgs)

        # checking
        cellMetadataDf = io_with_retries(fakesNamespaceArgs.output_metadata, "r", pandas.read_csv)

        features = io_with_retries(fakesNamespaceArgs.input_boundaries, "r", gpd.read_file)
        features.rename(columns={"geometry": SegmentationResult.geometry_field}, inplace=True)

        cellsCount = len(features)
        for featureIdx in range(cellsCount):
            poly: Polygon = geometry.shape(features.at[featureIdx, "Geometry"])

            assert poly.area * zDepth == cellMetadataDf["volume"][featureIdx]
            assert poly.centroid.x == cellMetadataDf["center_x"][featureIdx]
            assert poly.centroid.y == cellMetadataDf["center_y"][featureIdx]

            assert poly.bounds[0] == cellMetadataDf["min_x"][featureIdx]
            assert poly.bounds[1] == cellMetadataDf["min_y"][featureIdx]
            assert poly.bounds[2] == cellMetadataDf["max_x"][featureIdx]
            assert poly.bounds[3] == cellMetadataDf["max_y"][featureIdx]

        # deleting temporary file
        if os.path.exists(fakesNamespaceArgs.output_metadata):
            os.remove(fakesNamespaceArgs.output_metadata)
    finally:
        temp_dir.clear_dir()


@pytest.mark.parametrize("fov_size", [10, 100, 200, 250, 500, 2000], ids=str)
def test_cells_reader_row_groups(fov_size: int):
    input_boundaries = str(TEST_DATA_ROOT / "cells_cellpose_row_groups.parquet")
    all_cells_data = io_with_retries(input_boundaries, "rb", gpd.read_parquet)

    td = tempfile.TemporaryDirectory()
    geojson_path = str(td.name + "/cells_cellpose_row_groups.geojson")
    save_geodataframe(all_cells_data[:1], geojson_path)

    readers = [CellsParquetReader(input_boundaries), CellsGeoReader(geojson_path)]
    readers[1]._initialize_with_data(all_cells_data)

    readed_data = [[] for _ in readers]
    for i, reader in enumerate(readers):
        reader._set_cells_per_fov(fov_size)
        for fov_i in range(reader.get_fovs_count()):
            readed_data[i].extend(reader.read_fov(fov_i))

    assert len(readed_data[0]) == len(readed_data[1])
    assert readed_data[0] == readed_data[1]

    td.cleanup()
