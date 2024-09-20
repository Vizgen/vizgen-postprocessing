import os
from argparse import Namespace

import numpy
import pandas as pd
import pytest
from geopandas import gpd
from vpt_core.io.vzgfs import io_with_retries
from vpt_core.utils.copy_utils import _copy_between_filesystems

from tests.vpt import OUTPUT_FOLDER, TEST_DATA_ROOT
from tests.vpt.temp_dir import LocalTempDir, TempDir
from vpt.partition_transcripts.cell_x_gene import get_chunks, write_detected_transcripts
from vpt.partition_transcripts.run_partition_transcripts import main_partition_transcripts


def read_dataframe(path: str):
    if path.endswith(".csv"):
        return io_with_retries(path, "r", pd.read_csv)
    elif path.endswith(".parquet"):
        return io_with_retries(path, "rb", pd.read_parquet)
    raise NotImplementedError()


def write_dataframe(df: pd.DataFrame, path: str, **kwargs):
    if path.endswith(".csv"):
        return io_with_retries(path, "w", df.to_csv, **kwargs)
    elif path.endswith(".parquet"):
        return io_with_retries(path, "wb", df.to_parquet, **kwargs)
    raise NotImplementedError()


def get_arguments(temp_path: TempDir, df_format: str):
    path = temp_path.get_temp_path()
    sep = temp_path.get_sep()

    args = Namespace(
        input_boundaries=sep.join([path, "cells_cellpose.parquet"]),
        input_transcripts=sep.join([path, f"detected_transcripts.{df_format}"]),
        output_entity_by_gene=sep.join([path, "test_output_cell_by_gene.csv"]),
        output_transcripts=sep.join([path, f"detected_transcripts_cell_id.{df_format}"]),
        chunk_size=10000,
        overwrite=True,
    )
    _copy_between_filesystems(str(TEST_DATA_ROOT / "cells_cellpose.parquet"), args.input_boundaries)
    _copy_between_filesystems(str(TEST_DATA_ROOT / f"detected_transcripts.{df_format}"), args.input_transcripts)
    return args


@pytest.mark.parametrize("df_format", ["csv", "parquet"], ids=str)
@pytest.mark.parametrize("temp_dir", [LocalTempDir()], ids=str)
def test_func_partition_barcodes(temp_dir: TempDir, df_format: str):
    try:
        args = get_arguments(temp_dir, df_format)
        main_partition_transcripts(args)

        exprMatrixDf = io_with_retries(args.output_entity_by_gene, "r", callback=pd.read_csv)
        transcripts = read_dataframe(args.input_transcripts)

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


@pytest.mark.parametrize("df_format", ["csv", "parquet"], ids=str)
@pytest.mark.parametrize("temp_dir", [LocalTempDir()], ids=str)
def test_func_partition_barcodes_new_transcripts(temp_dir: TempDir, df_format: str):
    REQUIRED_COLUMNS = set(
        [
            "barcode_id",
            "global_x",
            "global_y",
            "global_z",
            "x",
            "y",
            "fov",
            "gene",
            "transcript_id",
            "cell_id",
        ]
    )
    try:
        args = get_arguments(temp_dir, df_format)
        main_partition_transcripts(args)

        original_transcripts = read_dataframe(args.input_transcripts)
        new_transcripts = read_dataframe(args.output_transcripts)

        assert len(original_transcripts) == len(new_transcripts)
        assert len(numpy.unique(new_transcripts.loc[:, "cell_id"].values)) > 1
        assert (
            set(new_transcripts.columns) >= REQUIRED_COLUMNS
        ), f"Missing column(s): {REQUIRED_COLUMNS - set(new_transcripts.columns)}"
    finally:
        temp_dir.clear_dir()


@pytest.mark.parametrize("df_format", ["csv", "parquet"], ids=str)
@pytest.mark.parametrize("temp_dir", [LocalTempDir()], ids=str)
def test_func_partition_barcodes_zero_transcripts(temp_dir: TempDir, df_format: str):
    try:
        args = get_arguments(temp_dir, df_format)

        # substitute the input transcripts with an empty dataframe
        unused_transcripts = read_dataframe(args.input_transcripts)
        write_dataframe(unused_transcripts.loc[[]], args.input_transcripts, index=False)

        main_partition_transcripts(args)

        original_transcripts = read_dataframe(args.input_transcripts)
        new_transcripts = read_dataframe(args.output_transcripts)

        assert len(original_transcripts) == len(new_transcripts)
        assert os.path.exists(args.output_entity_by_gene)
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


@pytest.mark.parametrize("input_file_name", ["test_non_segmented.parquet", "test_pre_segmented.parquet"])
@pytest.mark.parametrize("temp_dir", [LocalTempDir()], ids=str)
def test_io_parquet_detected_transcripts(temp_dir: TempDir, input_file_name: str):
    path = temp_dir.get_temp_path()
    sep = temp_dir.get_sep()

    input_file_path = str(TEST_DATA_ROOT / input_file_name)
    output_file_name = sep.join([path, f"{input_file_name[0:10]}_output.parquet"])

    append = False
    for chunk_df in get_chunks(input_file_path, 300):
        # This operation happens in /src/vpt/partition_transcripts/cell_x_gene.py#L139
        # And can introduce a crash if there are multiple columns named ""
        chunk_df = chunk_df.rename(columns={chunk_df.columns[0]: ""})

        write_detected_transcripts(chunk_df, output_file_name, append=append)
        append = True
