import os
import shutil
import zipfile
from argparse import Namespace

import pytest
from vpt_core.io.vzgfs import initialize_filesystem, vzg_open, retrying_attempts
from vpt_core.utils.copy_utils import _copy_between_filesystems

from tests.vpt import OUTPUT_FOLDER, TEST_DATA_ROOT
from tests.vpt.temp_dir import LocalTempDir, TempDir
from vpt import IS_VPT_EXPERIMENTAL_VAR
from vpt.vizgen_postprocess import main
from vpt.cmd_args import get_postprocess_parser as get_parser


def get_arguments(temp_dir: TempDir):
    path = temp_dir.get_temp_path()
    sep = temp_dir.get_sep()

    args = Namespace(
        subparser_name="update-vzg",
        input_boundaries=sep.join([path, "cells_cellpose.parquet"]),
        input_vzg=sep.join([path, "fake_vzg.vzg"]),
        output_vzg=sep.join([path, "test_vzg.vzg"]),
        input_entity_by_gene=sep.join([path, "cell_by_gene.csv"]),
        input_metadata=None,
        input_entity_type=None,
        temp_path=str(OUTPUT_FOLDER / "temp"),
        z_count=1,
        processes=2,
        overwrite=True,
        profile_execution_time=None,
        verbose=False,
        log_level=1,
        log_file=None,
        aws_profile_name=None,
        aws_access_key=None,
        aws_secret_key=None,
        gcs_service_account_key=None,
        dask_address=None,
    )

    _copy_between_filesystems(str(TEST_DATA_ROOT / "cells_cellpose.parquet"), args.input_boundaries)
    _copy_between_filesystems(str(TEST_DATA_ROOT / "fake_vzg.vzg"), args.input_vzg)
    _copy_between_filesystems(str(TEST_DATA_ROOT / "cell_by_gene.csv"), args.input_entity_by_gene)

    return args


def get_two_features_arguments(temp_dir: TempDir):
    path = temp_dir.get_temp_path()
    sep = temp_dir.get_sep()

    args = Namespace(
        subparser_name="update-vzg",
        input_boundaries=sep.join([path, "cells_cellpose.parquet"]),
        second_boundaries=sep.join([path, "cells_cellpose.parquet"]),
        input_vzg=sep.join([path, "fake_vzg.vzg"]),
        output_vzg=sep.join([path, "test_vzg.vzg"]),
        input_entity_by_gene=sep.join([path, "cell_by_gene.csv"]),
        second_entity_by_gene=sep.join([path, "cell_by_gene.csv"]),
        input_metadata=None,
        second_metadata=None,
        input_entity_type=None,
        second_entity_type="nuc",
        temp_path=str(OUTPUT_FOLDER / "temp"),
        z_count=1,
        processes=2,
        overwrite=True,
        profile_execution_time=None,
        verbose=False,
        log_level=1,
        log_file=None,
        aws_profile_name=None,
        aws_access_key=None,
        aws_secret_key=None,
        gcs_service_account_key=None,
        dask_address=None,
    )

    _copy_between_filesystems(str(TEST_DATA_ROOT / "cells_cellpose.parquet"), args.input_boundaries)
    _copy_between_filesystems(str(TEST_DATA_ROOT / "cells_cellpose.parquet"), args.second_boundaries)
    _copy_between_filesystems(str(TEST_DATA_ROOT / "fake_vzg.vzg"), args.input_vzg)
    _copy_between_filesystems(str(TEST_DATA_ROOT / "cell_by_gene.csv"), args.input_entity_by_gene)

    return args


def func_update_vzg(fakesNamespaceArgs, feature_name: str):
    main(fakesNamespaceArgs)

    datasetPath = os.path.join(fakesNamespaceArgs.temp_path, "fake_vzg")
    for attempt in retrying_attempts():
        with attempt, vzg_open(fakesNamespaceArgs.output_vzg, "rb") as f:
            with zipfile.ZipFile(f, "r") as zip_ref:
                zip_ref.extractall(datasetPath)

    for lodType in ["max", "min", "middle"]:
        cellsBinFilesList = os.listdir(os.path.join(datasetPath, "features", feature_name, "cells_packed", lodType))
        assert len(cellsBinFilesList) == 7 + 2

    # deleting temporary file
    if os.path.exists(fakesNamespaceArgs.temp_path):
        shutil.rmtree(fakesNamespaceArgs.temp_path)

    if os.path.exists(fakesNamespaceArgs.output_vzg):
        os.remove(fakesNamespaceArgs.output_vzg)


@pytest.mark.parametrize("temp_dir", [LocalTempDir()], ids=str)
def test_func_local_update_vzg(temp_dir: TempDir):
    experimental = os.environ[IS_VPT_EXPERIMENTAL_VAR]
    os.environ[IS_VPT_EXPERIMENTAL_VAR] = "false"
    initialize_filesystem()
    try:
        args = get_arguments(temp_dir)
        func_update_vzg(args, "cell")
    finally:
        os.environ[IS_VPT_EXPERIMENTAL_VAR] = experimental
        temp_dir.clear_dir()


@pytest.mark.parametrize("temp_dir", [LocalTempDir()], ids=str)
def test_two_features_local_update_vzg(temp_dir: TempDir):
    initialize_filesystem()
    try:
        args = get_two_features_arguments(temp_dir)
        func_update_vzg(args, "cell")
        func_update_vzg(args, "nuc")
    finally:
        temp_dir.clear_dir()


def test_two_features_args_parsing(temp_dir: TempDir = LocalTempDir()):
    experimental = os.environ[IS_VPT_EXPERIMENTAL_VAR]
    try:
        namespace = get_two_features_arguments(temp_dir)
        args_to_parse = [
            "--log-level",
            str(namespace.log_level),
            "--processes",
            str(namespace.processes),
            "update-vzg",
            "--input-boundaries",
            namespace.input_boundaries,
            "--second-boundaries",
            namespace.second_boundaries,
            "--input-vzg",
            namespace.input_vzg,
            "--output-vzg",
            namespace.output_vzg,
            "--input-entity-by-gene",
            namespace.input_entity_by_gene,
            "--second-entity-by-gene",
            namespace.second_entity_by_gene,
            "--second-entity-type",
            namespace.second_entity_type,
            "--temp-path",
            namespace.temp_path,
            "--overwrite",
        ]
        os.environ[IS_VPT_EXPERIMENTAL_VAR] = "false"
        with pytest.raises(SystemExit):
            get_parser().parse_args(args_to_parse)

        os.environ[IS_VPT_EXPERIMENTAL_VAR] = "true"
        args = get_parser().parse_args(args_to_parse)
        func_update_vzg(args, "cell")
        func_update_vzg(args, "nuc")

    finally:
        os.environ[IS_VPT_EXPERIMENTAL_VAR] = experimental
        temp_dir.clear_dir()
