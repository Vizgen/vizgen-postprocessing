import csv
import os.path
from argparse import Namespace
from pathlib import Path
from typing import Optional

import geopandas as gpd
import pytest
from geopandas import GeoDataFrame

from tests import TEST_DATA_ROOT, OUTPUT_FOLDER
from tests.base_case import BaseCase
from tests.segmentation_utils import assert_df_equals
from vpt.convert_geometry.main import convert_geometry
from vpt.segmentation.utils.seg_result import SegmentationResult


class ConvertCase(BaseCase):

    def __init__(self, name: str, input_path: str, output_path: str, map_path: str, gt_path: str,
                 convert_to_3D: bool, number_z_planes: Optional[int], spacing_z_planes: Optional[float]):
        super(ConvertCase, self).__init__(name)

        self.gt_path = gt_path
        self.output_path = output_path
        self.input_path = input_path
        self.map_path = map_path
        self.convert_to_3D = convert_to_3D
        self.number_z_planes = number_z_planes
        self.spacing_z_planes = spacing_z_planes
        self.file_field = 'SourceFilePath'

    def update_ids_with_map(self, dataframe: GeoDataFrame):
        with open(self.map_path, 'r') as f:
            csv_reader = csv.reader(f, delimiter=',')
            header = True
            source_id = 1
            entity_id = 2
            id_field = SegmentationResult.cell_id_field
            for row in csv_reader:
                if header:
                    source_file_path = row.index('SourceFilePath')
                    source_id = row.index('SourceID')
                    entity_id = row.index('EntityID')
                    header = False
                else:
                    df_filter = dataframe[id_field] is not None
                    if self.file_field in dataframe.columns:
                        dataframe[self.file_field] = dataframe[self.file_field].apply(lambda field:
                                                                                      str(TEST_DATA_ROOT / field))
                        df_filter = dataframe[self.file_field] == row[source_file_path]
                    id_filter = dataframe[id_field].astype('str') == row[source_id]
                    dataframe.loc[df_filter * id_filter, id_field] = int(row[entity_id])
        return dataframe

    def asset_parquet_equality(self):
        with open(self.output_path, 'rb') as f1:
            with open(self.gt_path, 'rb') as f2:
                data1 = gpd.read_parquet(f1)
                data2 = gpd.read_parquet(f2)

                data2 = self.update_ids_with_map(data2)

                data1 = data1[sorted(data1.columns)]
                data2 = data2[sorted(data2.columns)]

                if self.file_field in data2.columns:
                    data2.drop(columns=['SourceFilePath'], inplace=True)

                assert_df_equals(data1, data2)

    def assert_exist(self):
        assert os.path.exists(self.output_path)


CONVERT_CASES = [
    ConvertCase(
        name='hdf5',
        input_path=str(TEST_DATA_ROOT / 'test_convert_seg_segmentation.hdf5'),
        output_path=str(OUTPUT_FOLDER / 'cvt_hdf5.parquet'),
        map_path=str(OUTPUT_FOLDER / 'map_hdf5.csv'),
        gt_path=str(TEST_DATA_ROOT / 'cvt_hdf5_result.parquet'),
        convert_to_3D=False,
        number_z_planes=None,
        spacing_z_planes=None
    ),
    ConvertCase(
        name='qpath',
        input_path=str(TEST_DATA_ROOT / 'test_convert_seg_segmentation.geojson'),
        output_path=str(OUTPUT_FOLDER / 'cvt_geo.parquet'),
        map_path=str(OUTPUT_FOLDER / 'map_geo.csv'),
        gt_path=str(TEST_DATA_ROOT / 'cvt_1_geo_result.parquet'),
        convert_to_3D=False,
        number_z_planes=None,
        spacing_z_planes=None
    ),
    ConvertCase(
        name='qpath_multiple',
        input_path=str(TEST_DATA_ROOT / 'test_convert_seg_segmentatio(.*)[.]geojson'),
        output_path=str(OUTPUT_FOLDER / 'cvt_multi_geo.parquet'),
        map_path=str(OUTPUT_FOLDER / 'map_2_geo.csv'),
        gt_path=str(TEST_DATA_ROOT / 'cvt_2_geo_result.parquet'),
        convert_to_3D=False,
        number_z_planes=None,
        spacing_z_planes=None
    ),
    ConvertCase(
        name='qpath_replication',
        input_path=str(TEST_DATA_ROOT / 'test_convert_seg_segmentation.geojson'),
        output_path=str(OUTPUT_FOLDER / 'cvt_geo.parquet'),
        map_path=str(OUTPUT_FOLDER / 'map_3_geo.csv'),
        gt_path=str(TEST_DATA_ROOT / 'cvt_3_geo_result.parquet'),
        convert_to_3D=True,
        number_z_planes=4,
        spacing_z_planes=1
    ),
    ConvertCase(
        name='parquet',
        input_path=str(TEST_DATA_ROOT / 'cvt_parquet_result.parquet'),
        output_path=str(OUTPUT_FOLDER / 'cvt_parquet.parquet'),
        map_path=str(OUTPUT_FOLDER / 'map_parquet.csv'),
        gt_path=str(TEST_DATA_ROOT / 'cvt_parquet_result.parquet'),
        convert_to_3D=False,
        number_z_planes=None,
        spacing_z_planes=None
    ),
    ConvertCase(
        name='qpath_replication',
        input_path=str(TEST_DATA_ROOT / 'cvt_parquet_result.parquet'),
        output_path=str(OUTPUT_FOLDER / 'cvt_2_parquet.parquet'),
        map_path=str(OUTPUT_FOLDER / 'map_2_parquet.csv'),
        gt_path=str(TEST_DATA_ROOT / 'cvt_2_parquet_result.parquet'),
        convert_to_3D=True,
        number_z_planes=4,
        spacing_z_planes=1
    )
]


@pytest.mark.parametrize('case', CONVERT_CASES, ids=str)
def test_convert_geometry(case: ConvertCase) -> None:
    args = Namespace(
        input_boundaries=case.input_path,
        output_boundaries=case.output_path,
        entity_fusion_strategy='harmonize',
        output_entity_type='cell',
        id_mapping_file=case.map_path,
        max_row_group_size=17500,
        overwrite=True,
        convert_to_3D=case.convert_to_3D,
        number_z_planes=case.number_z_planes,
        spacing_z_planes=case.spacing_z_planes
    )
    Path(Path(case.output_path).parent).mkdir(exist_ok=True, parents=True)
    convert_geometry(args)
    case.assert_exist()
    case.asset_parquet_equality()


CONVERT_CASES_ARGS = [
    ConvertCase(
        name='hdf5',
        input_path=str(TEST_DATA_ROOT / 'test_convert_seg_segmentation.hdf5'),
        output_path='cvt_hdf5.parquet',
        map_path=str(OUTPUT_FOLDER / 'map.csv'),
        gt_path=str(TEST_DATA_ROOT / 'cvt_hdf5_result.parquet'),
        convert_to_3D=True,
        number_z_planes=2,
        spacing_z_planes=1.5
    ),
    ConvertCase(
        name='qpath',
        input_path=str(TEST_DATA_ROOT / 'test_convert_seg_segmentation.geojson'),
        output_path=str(OUTPUT_FOLDER / 'cvt_geo.parquet'),
        map_path=str(OUTPUT_FOLDER / 'map.csv'),
        gt_path=str(TEST_DATA_ROOT / 'cvt_1_geo_result.parquet'),
        convert_to_3D=True,
        number_z_planes=None,
        spacing_z_planes=1.5
    ),
    ConvertCase(
        name='qpath',
        input_path=str(TEST_DATA_ROOT / 'test_convert_seg_segmentation.geojson'),
        output_path=str(OUTPUT_FOLDER / 'cvt_geo.parquet'),
        map_path=str(OUTPUT_FOLDER / 'map.csv'),
        gt_path=str(TEST_DATA_ROOT / 'cvt_1_geo_result.parquet'),
        convert_to_3D=False,
        number_z_planes=2,
        spacing_z_planes=1
    ),
    ConvertCase(
        name='parquet',
        input_path=str(TEST_DATA_ROOT / 'cvt_parquet_result.parquet'),
        output_path=str(OUTPUT_FOLDER / 'cvt_geo.parquet'),
        map_path=str(OUTPUT_FOLDER / 'map.csv'),
        gt_path=str(TEST_DATA_ROOT / 'cvt_parquet_result.parquet'),
        convert_to_3D=True,
        number_z_planes=None,
        spacing_z_planes=1.5
    ),
]


@pytest.mark.parametrize('case', CONVERT_CASES_ARGS, ids=str)
def test_convert_geometry_arguments(case: ConvertCase) -> None:
    args = Namespace(
        input_boundaries=case.input_path,
        output_boundaries=case.output_path,
        entity_fusion_strategy='harmonize',
        output_entity_type='cell',
        max_row_group_size=17500,
        id_mapping_file=None,
        overwrite=True,
        convert_to_3D=case.convert_to_3D,
        number_z_planes=case.number_z_planes,
        spacing_z_planes=case.spacing_z_planes
    )
    try:
        convert_geometry(args)
        assert False
    except ValueError:
        pass
