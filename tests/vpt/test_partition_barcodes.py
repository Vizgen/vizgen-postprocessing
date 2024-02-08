import os
from argparse import Namespace
from functools import partial

import numpy
import pandas as pd
import pytest
from geopandas import gpd
from vpt_core.io.vzgfs import io_with_retries
from vpt_core.utils.copy_utils import _copy_between_filesystems

from tests.vpt import OUTPUT_FOLDER, TEST_DATA_ROOT
from tests.vpt.temp_dir import LocalTempDir, TempDir
from vpt.partition_transcripts.run_partition_transcripts import main_partition_transcripts


def get_arguments(temp_path: TempDir):
    path = temp_path.get_temp_path()
    sep = temp_path.get_sep()

    args = Namespace(
        input_boundaries=sep.join([path, "cells_cellpose.parquet"]),
        input_transcripts=sep.join([path, "detected_transcripts.csv"]),
        output_entity_by_gene=sep.join([path, "test_output_cell_by_gene.csv"]),
        output_transcripts=sep.join([path, "detected_transcripts_cell_id.csv"]),
        chunk_size=10000,
        overwrite=True,
    )
    _copy_between_filesystems(str(TEST_DATA_ROOT / "cells_cellpose.parquet"), args.input_boundaries)
    _copy_between_filesystems(str(TEST_DATA_ROOT / "detected_transcripts.csv"), args.input_transcripts)
    return args


@pytest.mark.parametrize("temp_dir", [LocalTempDir()], ids=str)
def test_func_partition_barcodes(temp_dir: TempDir):
    try:
        args = get_arguments(temp_dir)
        main_partition_transcripts(args)

        exprMatrixDf = io_with_retries(args.output_entity_by_gene, "r", callback=pd.read_csv)
        transcripts = io_with_retries(args.input_transcripts, "r", pd.read_csv)

        genesDetected = transcripts["gene"].unique()
        genesCount = len(genesDetected) - 1

        features = io_with_retries(args.input_boundaries, "rb", gpd.read_parquet)
        cellsCount = len(features)

        # dim check
        assert cellsCount, genesCount == exprMatrixDf.shape

        # check if all elements are not zeros
        assert numpy.any(exprMatrixDf.values)
    finally:
        temp_dir.clear_dir()


@pytest.mark.parametrize("temp_dir", [LocalTempDir()], ids=str)
def test_func_partition_barcodes_new_transcripts(temp_dir: TempDir):
    try:
        args = get_arguments(temp_dir)
        main_partition_transcripts(args)

        original_transcripts = io_with_retries(args.input_transcripts, "r", pd.read_csv)
        new_transcripts = io_with_retries(args.output_transcripts, "r", pd.read_csv)

        assert len(original_transcripts) == len(new_transcripts)
        assert len(numpy.unique(new_transcripts.loc[:, "cell_id"].values)) > 1
    finally:
        temp_dir.clear_dir()


@pytest.mark.parametrize("temp_dir", [LocalTempDir()], ids=str)
def test_func_partition_barcodes_zero_transcripts(temp_dir: TempDir):
    try:
        args = get_arguments(temp_dir)

        # substitute the input transcripts with an empty dataframe
        unused_transcripts = io_with_retries(args.input_transcripts, "r", pd.read_csv)
        io_with_retries(args.input_transcripts, "w", partial(unused_transcripts.loc[[]].to_csv, index=False))

        main_partition_transcripts(args)

        original_transcripts = io_with_retries(args.input_transcripts, "r", pd.read_csv)
        new_transcripts = io_with_retries(args.output_transcripts, "r", pd.read_csv)

        assert len(original_transcripts) == len(new_transcripts)
    finally:
        temp_dir.clear_dir()


@pytest.mark.parametrize(
    "fakesNamespaceArgs",
    [
        Namespace(
            input_boundaries=str(TEST_DATA_ROOT / "cells_cellpose.parquet"),
            input_transcripts=str(TEST_DATA_ROOT / "detected_transcripts_unordered_z.csv"),
            output_entity_by_gene=str(OUTPUT_FOLDER / "test_output_cell_by_gene.csv"),
            output_transcripts=str(OUTPUT_FOLDER / "detected_transcripts_cell_id.csv"),
            chunk_size=100,
            overwrite=True,
        ),
        Namespace(
            input_boundaries=str(TEST_DATA_ROOT / "cells_onez.parquet"),
            input_transcripts=str(TEST_DATA_ROOT / "detected_transcripts.csv"),
            output_entity_by_gene=str(OUTPUT_FOLDER / "unmatched_z_cell_by_gene.csv"),
            output_transcripts=str(OUTPUT_FOLDER / "unmatched_z_transcripts_cell_id.csv"),
            chunk_size=100,
            overwrite=True,
        ),
    ],
)
def test_transcripts_order(fakesNamespaceArgs: Namespace):
    main_partition_transcripts(fakesNamespaceArgs)

    original_transcripts = pd.read_csv(fakesNamespaceArgs.input_transcripts)
    new_transcripts = pd.read_csv(fakesNamespaceArgs.output_transcripts)

    assert (original_transcripts["global_x"] - new_transcripts["global_x"]).abs().max() < 1e-3

    # # deleting temporary file
    if os.path.exists(fakesNamespaceArgs.output_entity_by_gene):
        os.remove(fakesNamespaceArgs.output_entity_by_gene)
    if os.path.exists(fakesNamespaceArgs.output_transcripts):
        os.remove(fakesNamespaceArgs.output_transcripts)


@pytest.mark.parametrize("temp_dir", [LocalTempDir()], ids=str)
def test_no_cells(temp_dir: TempDir):
    import geopandas as gpd

    path = temp_dir.get_temp_path()
    sep = temp_dir.get_sep()

    bnd_path = sep.join([path, "bnd.parquet"])
    output_cxg = sep.join([path, "output_cxg.csv"])
    output_tr = sep.join([path, "output_tr.csv"])
    tr_path = sep.join([path, "detected_transcripts.csv"])

    try:
        _copy_between_filesystems(str(TEST_DATA_ROOT / "detected_transcripts.csv"), tr_path)

        normal_gdf = gpd.read_parquet(TEST_DATA_ROOT / "cells_cellpose.parquet")
        empty_gdf = normal_gdf.drop(normal_gdf.index)
        io_with_retries(bnd_path, "wb", empty_gdf.to_parquet)

        args = Namespace(
            input_boundaries=bnd_path,
            input_transcripts=tr_path,
            output_entity_by_gene=output_cxg,
            output_transcripts=output_tr,
            chunk_size=100,
            overwrite=True,
        )
        main_partition_transcripts(args)
    finally:
        temp_dir.clear_dir()
