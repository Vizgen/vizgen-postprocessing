import argparse
import os
import shutil
import tempfile
import zipfile
from argparse import Namespace
from dataclasses import fields
from unittest import mock

import pytest
from vpt_core.io.vzgfs import initialize_filesystem, retrying_attempts, vzg_open
from vpt_core.utils.copy_utils import _copy_between_filesystems

from tests.vpt import OUTPUT_FOLDER, TEST_DATA_ROOT
from tests.vpt.temp_dir import LocalTempDir, TempDir
from vpt import IS_VPT_EXPERIMENTAL_VAR
from vpt.cmd_args import get_postprocess_parser as get_parser
from vpt.update_vzg.cmd_args import UpdateVzgArgs
from vpt.update_vzg.run_update_vzg import _construct_entity_types_list, _create_missing_metadata, main_update_vzg
from vpt.vizgen_postprocess import main


class PartialUpdateVzgArgs(UpdateVzgArgs):
    def __init__(self, **kwargs):
        for field in fields(UpdateVzgArgs):
            kwargs.setdefault(field.name, None)
        super().__init__(**kwargs)


def get_arguments(temp_dir: TempDir, vzg2: bool):
    input_file_name = "fake_vzg2.vzg2" if vzg2 else "fake_vzg.vzg"
    output_file_name = "test_vzg2.vzg2" if vzg2 else "test_vzg.vzg"

    path = temp_dir.get_temp_path()
    sep = temp_dir.get_sep()

    args = Namespace(
        subparser_name="update-vzg",
        input_boundaries=sep.join([path, "cells_cellpose.parquet"]),
        input_vzg=sep.join([path, input_file_name]),
        output_vzg=sep.join([path, output_file_name]),
        input_entity_by_gene=sep.join([path, "cell_by_gene.csv"]),
        input_metadata=None,
        input_entity_type=None,
        temp_path=str(OUTPUT_FOLDER / "temp"),
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
    )

    _copy_between_filesystems(str(TEST_DATA_ROOT / "cells_cellpose.parquet"), args.input_boundaries)
    _copy_between_filesystems(str(TEST_DATA_ROOT / input_file_name), args.input_vzg)
    _copy_between_filesystems(str(TEST_DATA_ROOT / "cell_by_gene.csv"), args.input_entity_by_gene)

    return args


def get_two_features_arguments(temp_dir: TempDir, vzg2: bool):
    input_file_name = "fake_vzg2.vzg2" if vzg2 else "fake_vzg.vzg"
    output_file_name = "test_vzg2.vzg2" if vzg2 else "test_vzg.vzg"

    path = temp_dir.get_temp_path()
    sep = temp_dir.get_sep()

    args = Namespace(
        subparser_name="update-vzg",
        input_boundaries=sep.join([path, "cells_cellpose.parquet"]),
        second_boundaries=sep.join([path, "cells_cellpose.parquet"]),
        input_vzg=sep.join([path, input_file_name]),
        output_vzg=sep.join([path, output_file_name]),
        input_entity_by_gene=sep.join([path, "cell_by_gene.csv"]),
        second_entity_by_gene=sep.join([path, "cell_by_gene.csv"]),
        input_metadata=None,
        second_metadata=None,
        input_entity_type=None,
        second_entity_type="nuc",
        temp_path=str(OUTPUT_FOLDER / "temp"),
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
    )

    _copy_between_filesystems(str(TEST_DATA_ROOT / "cells_cellpose.parquet"), args.input_boundaries)
    _copy_between_filesystems(str(TEST_DATA_ROOT / "cells_cellpose.parquet"), args.second_boundaries)
    _copy_between_filesystems(str(TEST_DATA_ROOT / input_file_name), args.input_vzg)
    _copy_between_filesystems(str(TEST_DATA_ROOT / "cell_by_gene.csv"), args.input_entity_by_gene)

    return args


def func_update_vzg(fakesNamespaceArgs, feature_name: str):
    main(fakesNamespaceArgs)

    if not fakesNamespaceArgs.output_vzg.endswith("vzg2"):
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


@pytest.mark.parametrize("vzg2", [True, False], ids=str)
@pytest.mark.parametrize("temp_dir", [LocalTempDir()], ids=str)
def test_func_local_update_vzg(temp_dir: TempDir, vzg2: bool):
    experimental = os.environ[IS_VPT_EXPERIMENTAL_VAR]
    os.environ[IS_VPT_EXPERIMENTAL_VAR] = "false"
    initialize_filesystem()
    try:
        args = get_arguments(temp_dir, vzg2)
        func_update_vzg(args, "cell")
    finally:
        os.environ[IS_VPT_EXPERIMENTAL_VAR] = experimental
        temp_dir.clear_dir()


@pytest.mark.parametrize("vzg2", [True, False], ids=str)
@pytest.mark.parametrize("temp_dir", [LocalTempDir()], ids=str)
def test_two_features_local_update_vzg(temp_dir: TempDir, vzg2: bool):
    initialize_filesystem()
    try:
        args = get_two_features_arguments(temp_dir, vzg2)
        func_update_vzg(args, "cell")
        func_update_vzg(args, "nuc")
    finally:
        temp_dir.clear_dir()


@pytest.mark.parametrize("vzg2", [True, False])
def test_two_features_args_parsing(vzg2: bool, temp_dir: TempDir = LocalTempDir()):
    experimental = os.environ[IS_VPT_EXPERIMENTAL_VAR]
    try:
        namespace = get_two_features_arguments(temp_dir, vzg2)
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


@pytest.mark.parametrize(
    "args, expected_answer",
    [
        (
            PartialUpdateVzgArgs(
                input_entity_type="type1",
            ),
            ["type1"],
        ),
        (
            PartialUpdateVzgArgs(
                input_entity_type="type1",
                second_boundaries="some_path",
                second_entity_type="type2",
            ),
            ["type1", "type2"],
        ),
        (
            PartialUpdateVzgArgs(
                input_boundaries=str(TEST_DATA_ROOT / "cells_cellpose.parquet"),
            ),
            ["cell"],
        ),
        (
            PartialUpdateVzgArgs(
                input_boundaries=str(TEST_DATA_ROOT / "cells_cellpose.parquet"),
                second_boundaries="some_path",
                second_entity_type="nucleus",
            ),
            ["cell", "nucleus"],
        ),
        (
            PartialUpdateVzgArgs(
                input_boundaries=str(TEST_DATA_ROOT / "cells_cellpose.parquet"),
                second_boundaries=str(TEST_DATA_ROOT / "cells_cellpose.parquet"),
            ),
            ["cell", "cell_2"],
        ),
    ],
)
def test_construct_entity_types_list(args, expected_answer):
    assert _construct_entity_types_list(args) == expected_answer


@mock.patch("vpt.update_vzg.run_update_vzg.create_input_metadata")
def test_create_missing_metadata(mock_create_input_metadata):
    # all metadata provided, one feature set
    _create_missing_metadata(
        PartialUpdateVzgArgs(input_boundaries="path1", input_metadata="path2"), "workdir", ["cell"]
    )
    mock_create_input_metadata.assert_not_called()
    mock_create_input_metadata.reset_mock()

    # all metadata provided, two feature sets
    _create_missing_metadata(
        PartialUpdateVzgArgs(
            input_boundaries="path0", input_metadata="path1", second_boundaries="path2", second_metadata="path3"
        ),
        "workdir",
        ["some_type", "some_other_type"],
    )
    mock_create_input_metadata.assert_not_called()
    mock_create_input_metadata.reset_mock()

    # metadata provided only for secondary features set
    _create_missing_metadata(
        PartialUpdateVzgArgs(input_boundaries="path1", second_boundaries="path2", second_metadata="path3"),
        "workdir",
        ["some_type", "some_other_type"],
    )
    mock_create_input_metadata.assert_called_once_with("workdir", "path1", "some_type")
    mock_create_input_metadata.reset_mock()

    # metadata provided only for primary features set
    _create_missing_metadata(
        PartialUpdateVzgArgs(input_boundaries="path1", input_metadata="path2", second_boundaries="path3"),
        "workdir",
        ["some_type", "some_other_type"],
    )
    mock_create_input_metadata.assert_called_once_with("workdir", "path3", "some_other_type")
    mock_create_input_metadata.reset_mock()

    # no metadata provided, two feature sets
    _create_missing_metadata(
        PartialUpdateVzgArgs(input_boundaries="path1", second_boundaries="path2"),
        "workdir",
        ["some_type", "some_other_type"],
    )
    assert mock_create_input_metadata.call_args_list == [
        mock.call("workdir", "path1", "some_type"),
        mock.call("workdir", "path2", "some_other_type"),
    ]


@mock.patch("vpt.update_vzg.run_update_vzg.UpdateVzgArgs", lambda **kwargs: PartialUpdateVzgArgs(**kwargs))
@mock.patch("vpt.update_vzg.run_update_vzg.validate_args", mock.MagicMock())
@mock.patch("vpt.update_vzg.run_update_vzg.update_vzg2")
@mock.patch("vpt.update_vzg.run_update_vzg.update_vzg")
def test_main_update_vzg(mock_update_vzg, mock_update_vzg2):
    with tempfile.TemporaryDirectory() as td:
        # vzg format
        main_update_vzg(
            argparse.Namespace(
                input_boundaries=str(TEST_DATA_ROOT / "cells_cellpose.parquet"),
                input_vzg="some/folder/test.vzg",
                temp_path=td,
            )
        )
        mock_update_vzg.assert_called_once()
        mock_update_vzg2.assert_not_called()

        mock_update_vzg.reset_mock()
        mock_update_vzg2.reset_mock()

        # vzg2 format
        main_update_vzg(
            argparse.Namespace(
                input_boundaries=str(TEST_DATA_ROOT / "cells_cellpose.parquet"),
                input_vzg="some/folder/test.vzg2",
                temp_path=td,
            )
        )
        mock_update_vzg2.assert_called_once()
        mock_update_vzg.assert_not_called()
