import tempfile

import geopandas
import numpy as np
import pyarrow.parquet as pq

from vpt.utils.output_tools import save_geodataframe, save_geodataframe_with_row_groups


def test_empty():
    with tempfile.TemporaryDirectory() as td:
        output_path = str(td + '/' + 'test_save_geodataframe_empty.geojson')
        save_geodataframe(geopandas.GeoDataFrame(), output_path)
        assert geopandas.read_file(output_path).empty


def test_row_groups():
    geometry = geopandas.GeoSeries.from_xy(*np.random.random((2, 500)))
    gdf = geopandas.GeoDataFrame({'a': np.random.random(500),
                                  'b': np.random.choice(list('abc'), size=500),
                                  'geometry': geometry}, index=np.random.permutation(range(500)))

    group_sizes = 10 + np.diff([0, *sorted(np.random.choice(range(400), size=9, replace=False)), 400])

    with tempfile.TemporaryDirectory() as td:
        output_path = str(td + '/' + 'test_row_groups.parquet')
        save_geodataframe_with_row_groups(gdf, output_path, group_sizes)

        assert gdf.equals(geopandas.read_parquet(output_path))

        with open(output_path, 'rb') as f:
            file = pq.ParquetFile(f)

            read_group_sizes = np.array([len(file.read_row_group(i)) for i in range(file.num_row_groups)])

            assert all(group_sizes == read_group_sizes)
