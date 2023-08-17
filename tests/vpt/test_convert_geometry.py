import csv
import os.path
import tempfile
from argparse import Namespace
from pathlib import Path
from typing import Optional

import geopandas as gpd
import pytest
from geopandas import GeoDataFrame
from vpt_core.segmentation.seg_result import SegmentationResult
from vpt_core.utils.base_case import BaseCase
from vpt_core.utils.segmentation_utils import assert_df_equals

from tests.vpt import OUTPUT_FOLDER, TEST_DATA_ROOT
from vpt.convert_geometry.main import convert_geometry
from vpt.convert_geometry import cmd_args


class ConvertCase(BaseCase):
    def __init__(
        self,
        name: str,
        input_path: str,
        output_path: str,
        map_path: str,
        gt_path: str,
        convert_to_3D: bool,
        number_z_planes: Optional[int],
        spacing_z_planes: Optional[float],
        transform_path: Optional[str],
    ):
        super(ConvertCase, self).__init__(name)

        self.gt_path = gt_path
        self.output_path = output_path
        self.input_path = input_path
        self.map_path = map_path
        self.convert_to_3D = convert_to_3D
        self.number_z_planes = number_z_planes
        self.spacing_z_planes = spacing_z_planes
        self.file_field = "SourceFilePath"
        self.transform_path = transform_path

    def update_ids_with_map(self, dataframe: GeoDataFrame):
        with open(self.map_path, "r") as f:
            csv_reader = csv.reader(f, delimiter=",")
            header = True
            source_id = 1
            entity_id = 2
            id_field = SegmentationResult.cell_id_field
            for row in csv_reader:
                if header:
                    source_file_path = row.index("SourceFilePath")
                    source_id = row.index("SourceID")
                    entity_id = row.index("EntityID")
                    header = False
                else:
                    df_filter = dataframe[id_field] is not None
                    if self.file_field in dataframe.columns:
                        dataframe[self.file_field] = dataframe[self.file_field].apply(
                            lambda field: str(TEST_DATA_ROOT / field)
                        )
                        df_filter = dataframe[self.file_field] == row[source_file_path]
                    id_filter = dataframe[id_field].astype("str") == row[source_id]
                    dataframe.loc[df_filter * id_filter, id_field] = int(row[entity_id])
        return dataframe

    def asset_parquet_equality(self):
        with open(self.output_path, "rb") as f1:
            with open(self.gt_path, "rb") as f2:
                data1 = gpd.read_parquet(f1)
                data2 = gpd.read_parquet(f2)

                data2 = self.update_ids_with_map(data2)

                data1 = data1[sorted(data1.columns)]
                data2 = data2[sorted(data2.columns)]

                if self.file_field in data2.columns:
                    data2.drop(columns=["SourceFilePath"], inplace=True)

                assert_df_equals(data1, data2)

    def assert_exist(self):
        assert os.path.exists(self.output_path)


CONVERT_CASES = [
    ConvertCase(
        name="hdf5",
        input_path=str(TEST_DATA_ROOT / "test_convert_seg_segmentation.hdf5"),
        output_path=str(OUTPUT_FOLDER / "cvt_hdf5.parquet"),
        map_path=str(OUTPUT_FOLDER / "map_hdf5.csv"),
        gt_path=str(TEST_DATA_ROOT / "cvt_hdf5_result.parquet"),
        convert_to_3D=False,
        number_z_planes=None,
        spacing_z_planes=None,
        transform_path=None,
    ),
    ConvertCase(
        name="qpath",
        input_path=str(TEST_DATA_ROOT / "test_convert_seg_segmentation.geojson"),
        output_path=str(OUTPUT_FOLDER / "cvt_geo.parquet"),
        map_path=str(OUTPUT_FOLDER / "map_geo.csv"),
        gt_path=str(TEST_DATA_ROOT / "cvt_1_geo_result.parquet"),
        convert_to_3D=False,
        number_z_planes=None,
        spacing_z_planes=None,
        transform_path=None,
    ),
    ConvertCase(
        name="qpath_multiple",
        input_path=str(TEST_DATA_ROOT / "test_convert_seg_segmentatio(.*)[.]geojson"),
        output_path=str(OUTPUT_FOLDER / "cvt_multi_geo.parquet"),
        map_path=str(OUTPUT_FOLDER / "map_2_geo.csv"),
        gt_path=str(TEST_DATA_ROOT / "cvt_2_geo_result.parquet"),
        convert_to_3D=False,
        number_z_planes=None,
        spacing_z_planes=None,
        transform_path=None,
    ),
    ConvertCase(
        name="qpath_replication",
        input_path=str(TEST_DATA_ROOT / "test_convert_seg_segmentation.geojson"),
        output_path=str(OUTPUT_FOLDER / "cvt_geo.parquet"),
        map_path=str(OUTPUT_FOLDER / "map_3_geo.csv"),
        gt_path=str(TEST_DATA_ROOT / "cvt_3_geo_result.parquet"),
        convert_to_3D=True,
        number_z_planes=4,
        spacing_z_planes=1,
        transform_path=None,
    ),
    ConvertCase(
        name="parquet",
        input_path=str(TEST_DATA_ROOT / "cvt_parquet_result.parquet"),
        output_path=str(OUTPUT_FOLDER / "cvt_parquet.parquet"),
        map_path=str(OUTPUT_FOLDER / "map_parquet.csv"),
        gt_path=str(TEST_DATA_ROOT / "cvt_parquet_result.parquet"),
        convert_to_3D=False,
        number_z_planes=None,
        spacing_z_planes=None,
        transform_path=None,
    ),
    ConvertCase(
        name="qpath_replication",
        input_path=str(TEST_DATA_ROOT / "cvt_parquet_result.parquet"),
        output_path=str(OUTPUT_FOLDER / "cvt_2_parquet.parquet"),
        map_path=str(OUTPUT_FOLDER / "map_2_parquet.csv"),
        gt_path=str(TEST_DATA_ROOT / "cvt_2_parquet_result.parquet"),
        convert_to_3D=True,
        number_z_planes=4,
        spacing_z_planes=1,
        transform_path=None,
    ),
]


@pytest.mark.parametrize("case", CONVERT_CASES, ids=str)
def test_convert_geometry(case: ConvertCase) -> None:
    args = Namespace(
        input_boundaries=case.input_path,
        output_boundaries=case.output_path,
        entity_fusion_strategy="harmonize",
        output_entity_type="cell",
        id_mapping_file=case.map_path,
        max_row_group_size=17500,
        overwrite=True,
        input_micron_to_mosaic=case.transform_path,
        convert_to_3D=case.convert_to_3D,
        number_z_planes=case.number_z_planes,
        spacing_z_planes=case.spacing_z_planes,
    )
    Path(Path(case.output_path).parent).mkdir(exist_ok=True, parents=True)
    convert_geometry(args)
    case.assert_exist()
    case.asset_parquet_equality()


CONVERT_CASES_ARGS = [
    ConvertCase(
        name="hdf5",
        input_path=str(TEST_DATA_ROOT / "test_convert_seg_segmentation.hdf5"),
        output_path="cvt_hdf5.parquet",
        map_path=str(OUTPUT_FOLDER / "map.csv"),
        gt_path=str(TEST_DATA_ROOT / "cvt_hdf5_result.parquet"),
        convert_to_3D=True,
        number_z_planes=2,
        spacing_z_planes=1.5,
        transform_path=None,
    ),
    ConvertCase(
        name="qpath",
        input_path=str(TEST_DATA_ROOT / "test_convert_seg_segmentation.geojson"),
        output_path=str(OUTPUT_FOLDER / "cvt_geo.parquet"),
        map_path=str(OUTPUT_FOLDER / "map.csv"),
        gt_path=str(TEST_DATA_ROOT / "cvt_1_geo_result.parquet"),
        convert_to_3D=True,
        number_z_planes=None,
        spacing_z_planes=1.5,
        transform_path=None,
    ),
    ConvertCase(
        name="qpath",
        input_path=str(TEST_DATA_ROOT / "test_convert_seg_segmentation.geojson"),
        output_path=str(OUTPUT_FOLDER / "cvt_geo.parquet"),
        map_path=str(OUTPUT_FOLDER / "map.csv"),
        gt_path=str(TEST_DATA_ROOT / "cvt_1_geo_result.parquet"),
        convert_to_3D=False,
        number_z_planes=2,
        spacing_z_planes=1,
        transform_path=None,
    ),
    ConvertCase(
        name="parquet",
        input_path=str(TEST_DATA_ROOT / "cvt_parquet_result.parquet"),
        output_path=str(OUTPUT_FOLDER / "cvt_geo.parquet"),
        map_path=str(OUTPUT_FOLDER / "map.csv"),
        gt_path=str(TEST_DATA_ROOT / "cvt_parquet_result.parquet"),
        convert_to_3D=True,
        number_z_planes=None,
        spacing_z_planes=1.5,
        transform_path=None,
    ),
]


@pytest.mark.parametrize("case", CONVERT_CASES_ARGS, ids=str)
def test_convert_geometry_arguments(case: ConvertCase) -> None:
    args = Namespace(
        input_boundaries=case.input_path,
        output_boundaries=case.output_path,
        entity_fusion_strategy="harmonize",
        output_entity_type="cell",
        max_row_group_size=17500,
        id_mapping_file=None,
        overwrite=True,
        input_micron_to_mosaic=case.transform_path,
        convert_to_3D=case.convert_to_3D,
        number_z_planes=case.number_z_planes,
        spacing_z_planes=case.spacing_z_planes,
    )
    try:
        convert_geometry(args)
        assert False
    except ValueError:
        pass


def test_validate_args_with_input():
    with pytest.raises(ValueError) as e:
        mock_args = cmd_args.ConvertGeometryArgs(
            input_boundaries="boundaries",
            output_boundaries="boundaries",
            output_entity_type="cell",
            entity_fusion_strategy="harmonize",
            id_mapping_file="map",
            max_row_group_size=100000,
            overwrite=False,
            input_micron_to_mosaic=None,
            number_z_planes=None,
            spacing_z_planes=None,
            convert_to_3D=False,
        )
        cmd_args.validate_args_with_input(mock_args, "fake_file.unsupported")
        assert "not supported" in str(e.value)

    with pytest.raises(ValueError) as e:
        mock_args = cmd_args.ConvertGeometryArgs(
            input_boundaries="boundaries",
            output_boundaries="boundaries",
            output_entity_type="cell",
            entity_fusion_strategy="harmonize",
            id_mapping_file="map",
            max_row_group_size=100000,
            overwrite=False,
            spacing_z_planes=0,
            number_z_planes=None,
            input_micron_to_mosaic=None,
            convert_to_3D=False,
        )
        cmd_args.validate_args_with_input(mock_args, "fake_file.parquet")
        assert "spacing" in str(e.value)

    with pytest.raises(ValueError) as e:
        mock_args = cmd_args.ConvertGeometryArgs(
            input_boundaries="boundaries",
            output_boundaries="boundaries",
            output_entity_type="cell",
            entity_fusion_strategy="harmonize",
            id_mapping_file="map",
            max_row_group_size=100000,
            overwrite=False,
            number_z_planes=0,
            input_micron_to_mosaic=None,
            spacing_z_planes=None,
            convert_to_3D=False,
        )
        cmd_args.validate_args_with_input(mock_args, "fake_file.parquet")
        assert "positive integer" in str(e.value)


def test_validate_args_micron_to_mosaic():
    with tempfile.NamedTemporaryFile() as tf:
        tf.write(b"Contents go here")
        tf.seek(0)
        mock_args = cmd_args.ConvertGeometryArgs(
            input_boundaries="boundaries",
            output_boundaries="boundaries",
            input_micron_to_mosaic=tf.name,
            output_entity_type="cell",
            entity_fusion_strategy="harmonize",
            id_mapping_file="map",
            max_row_group_size=100000,
            overwrite=False,
            number_z_planes=None,
            spacing_z_planes=None,
            convert_to_3D=False,
        )
        cmd_args.validate_cmd_args(mock_args)

    with pytest.raises(ValueError) as e:
        cmd_args.validate_cmd_args(mock_args)
        assert "should be a file" in str(e.value)


def test_validate_args_overwrite():
    with tempfile.TemporaryDirectory() as td:
        mock_args = cmd_args.ConvertGeometryArgs(
            input_boundaries="boundaries",
            output_boundaries=f"{td}/boundaries",
            output_entity_type="cell",
            entity_fusion_strategy="harmonize",
            id_mapping_file=f"{td}/map",
            max_row_group_size=100000,
            overwrite=False,
            input_micron_to_mosaic=None,
            number_z_planes=None,
            spacing_z_planes=None,
            convert_to_3D=False,
        )
        cmd_args.validate_cmd_args(mock_args)

        with pytest.raises(ValueError):
            with open(f"{td}/map", "w") as f:
                f.write("Contents go here")
            cmd_args.validate_cmd_args(mock_args)

        with pytest.raises(ValueError):
            with open(f"{td}/boundaries", "w") as f:
                f.write("Contents go here")
            cmd_args.validate_cmd_args(mock_args)


def test_validate_args_output_files():
    mock_args = cmd_args.ConvertGeometryArgs(
        input_boundaries="boundaries",
        output_boundaries=str(TEST_DATA_ROOT),
        output_entity_type="cell",
        entity_fusion_strategy="harmonize",
        id_mapping_file="map",
        max_row_group_size=100000,
        overwrite=False,
        input_micron_to_mosaic=None,
        number_z_planes=None,
        spacing_z_planes=None,
        convert_to_3D=False,
    )
    with pytest.raises(ValueError) as e:
        cmd_args.validate_cmd_args(mock_args)
        assert "should be a file" in str(e.value)

    mock_args = cmd_args.ConvertGeometryArgs(
        input_boundaries="boundaries",
        output_boundaries="boundaries",
        output_entity_type="cell",
        entity_fusion_strategy="harmonize",
        id_mapping_file="map",
        max_row_group_size=1,
        overwrite=False,
        input_micron_to_mosaic=None,
        number_z_planes=None,
        spacing_z_planes=None,
        convert_to_3D=False,
    )
    with pytest.raises(ValueError) as e:
        cmd_args.validate_cmd_args(mock_args)
        assert "Row group size" in str(e.value)
