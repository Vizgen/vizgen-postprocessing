# flake8: noqa

import numpy as np
import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import MultiPolygon

from tests.integration_cloud import TEST_S3_BUCKET_PATH, TEST_GCS_PATH
from tests.sum_signals.test_sum_signals import SumSignalsCaseScheme, SumSignalsCase, test_sum_signals, setup_from_scheme
from tests.temp_dir import CloudTempDir

SUM_SIGNALS_TEST_SCHEMES = [
    SumSignalsCaseScheme(f'{name}_z_layers', [(np.ones((100, 100)), 'c1', 1),
                                              (np.ones((100, 100)), 'c1', 2),
                                              (np.zeros((100, 100)), 'c1', 3)],
                         gpd.GeoDataFrame({'ID': range(3),
                                           'EntityID': [10439330, 10439330, 10439331],
                                           'Name': np.nan,
                                           'Type': ['cell'] * 3,
                                           'ParentID': np.nan,
                                           'ParentType': np.nan,
                                           'ZLevel': range(3),
                                           'ZIndex': range(1, 4),
                                           'Geometry': [
                                                    MultiPolygon([([(40, 40), (60, 40), (60, 60), (40, 60)], [])]),
                                                    MultiPolygon([([(40, 40), (60, 40), (60, 60), (40, 60)], [])]),
                                                    MultiPolygon([([(40, 40), (60, 40), (60, 60), (40, 60)],
                                                                   [])])]}).set_geometry('Geometry'),
                         np.eye(3),
                         pd.DataFrame({'c1_raw': [21 ** 2 * 2, 0], 'c1_high_pass': [0, 0]}, dtype=np.float64,
                                      index=[10439330, 10439331]),
                         1,
                         tmp_dir)
    for name, tmp_dir in zip(['s3', 'gcs'],
                             [CloudTempDir(TEST_S3_BUCKET_PATH), CloudTempDir(TEST_GCS_PATH)])
]


@pytest.mark.parametrize('scheme', SUM_SIGNALS_TEST_SCHEMES, ids=str)
def test_sum_signals_cloud(scheme: SumSignalsCaseScheme, setup_from_scheme: SumSignalsCase):
    test_sum_signals(scheme, setup_from_scheme)
