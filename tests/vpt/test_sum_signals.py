import argparse
import io

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import tifffile
from shapely.geometry import MultiPolygon
from vpt_core.io.vzgfs import initialize_filesystem, vzg_open, retrying_attempts, io_with_retries
from vpt_core.utils.base_case import BaseCase

from tests.vpt.temp_dir import LocalTempDir, TempDir
from vpt.sum_signals.main import sum_signals


class SumSignalsCaseScheme:
    def __init__(
        self,
        name: str,
        images: list,
        boundaries: gpd.GeoDataFrame,
        micron_to_mosaic: np.ndarray,
        answer: pd.DataFrame,
        workers: int,
        temp_dir: TempDir,
    ):
        self.name = name

        self.images = images
        self.boundaries = boundaries
        self.micron_to_mosaic = micron_to_mosaic
        self.workers = workers
        self.answer = answer

        self.temp_dir = temp_dir


class SumSignalsCase(BaseCase):
    def __init__(
        self,
        name: str,
        regex: str,
        boundaries_path: str,
        transform_path: str,
        output_path: str,
        answer: pd.DataFrame,
        workers: int,
    ):
        super().__init__(name)

        self.regex = regex
        self.boundaries_path = boundaries_path
        self.transform_path = transform_path
        self.output_path = output_path
        self.workers = workers

        self.answer = answer


SUM_SIGNALS_TEST_SCHEMES = [
    SumSignalsCaseScheme(
        "z_layers",
        [(np.ones((100, 100)), "c1", 1), (np.ones((100, 100)), "c1", 2), (np.zeros((100, 100)), "c1", 3)],
        gpd.GeoDataFrame(
            {
                "ID": range(3),
                "EntityID": [10439330, 10439330, 10439331],
                "Name": np.nan,
                "Type": ["cell"] * 3,
                "ParentID": np.nan,
                "ParentType": np.nan,
                "ZLevel": range(3),
                "ZIndex": range(1, 4),
                "Geometry": [
                    MultiPolygon([([(40, 40), (60, 40), (60, 60), (40, 60)], [])]),
                    MultiPolygon([([(40, 40), (60, 40), (60, 60), (40, 60)], [])]),
                    MultiPolygon([([(40, 40), (60, 40), (60, 60), (40, 60)], [])]),
                ],
            }
        ).set_geometry("Geometry"),
        np.eye(3),
        pd.DataFrame(
            {"c1_raw": [21**2 * 2, 0], "c1_high_pass": [0, 0]}, dtype=np.float64, index=[10439330, 10439331]
        ),
        workers=1,
        temp_dir=LocalTempDir(),
    ),
    SumSignalsCaseScheme(
        "z_layers",
        [(np.ones((100, 100)), "c1", 1), (np.ones((100, 100)), "c1", 2), (np.zeros((100, 100)), "c1", 3)],
        gpd.GeoDataFrame(
            {
                "ID": range(3),
                "EntityID": [10439330, 10439330, 10439331],
                "Name": np.nan,
                "Type": ["cell"] * 3,
                "ParentID": np.nan,
                "ParentType": np.nan,
                "ZLevel": range(3),
                "ZIndex": range(1, 4),
                "Geometry": [
                    MultiPolygon([([(40, 40), (60, 40), (60, 60), (40, 60)], [])]),
                    MultiPolygon([([(40, 40), (60, 40), (60, 60), (40, 60)], [])]),
                    MultiPolygon([([(40, 40), (60, 40), (60, 60), (40, 60)], [])]),
                ],
            }
        ).set_geometry("Geometry"),
        np.eye(3),
        pd.DataFrame(
            {"c1_raw": [21**2 * 2, 0], "c1_high_pass": [0, 0]}, dtype=np.float64, index=[10439330, 10439331]
        ),
        workers=4,
        temp_dir=LocalTempDir(),
    ),
]
initialize_filesystem()


@pytest.fixture()
def setup_from_scheme(scheme: SumSignalsCaseScheme) -> BaseCase:
    path = scheme.temp_dir.get_temp_path()
    sep = scheme.temp_dir.get_sep()

    for img, stain, z in scheme.images:
        for attempt in retrying_attempts():
            with attempt, io.BytesIO() as buffer:
                tifffile.imwrite(buffer, img)
                with vzg_open(sep.join([path, f"mosaic_{stain}_z{z}.tif"]), "wb") as f:
                    f.write(buffer.getvalue())
    regex = sep.join([path, r"mosaic_(?P<stain>[\w|-]+[0-9]?)_z(?P<z>[0-9]+).tif"])

    boundaries_path = sep.join([path, "boundaries.parquet"])
    io_with_retries(boundaries_path, "wb", scheme.boundaries.to_parquet)

    transform_path = sep.join([path, "transform.csv"])
    io_with_retries(transform_path, "wb", lambda f: np.savetxt(f, scheme.micron_to_mosaic))

    output_path = sep.join([path, "output.csv"])

    yield SumSignalsCase(
        scheme.name, regex, boundaries_path, transform_path, output_path, scheme.answer, scheme.workers
    )

    scheme.temp_dir.clear_dir()


@pytest.mark.parametrize("scheme", SUM_SIGNALS_TEST_SCHEMES, ids=str)
def test_sum_signals(scheme: SumSignalsCaseScheme, setup_from_scheme: SumSignalsCase):
    args = argparse.Namespace(
        input_images=setup_from_scheme.regex,
        input_boundaries=setup_from_scheme.boundaries_path,
        input_micron_to_mosaic=setup_from_scheme.transform_path,
        output_csv=setup_from_scheme.output_path,
        overwrite=True,
    )
    sum_signals(args)

    output_df = io_with_retries(setup_from_scheme.output_path, "r", lambda f: pd.read_csv(f, index_col=0))

    assert setup_from_scheme.answer.equals(output_df)
