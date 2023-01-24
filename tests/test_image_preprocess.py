import cv2
import pytest
import numpy as np
import shapely.geometry

from vpt.segmentation.filters.description import Header
from vpt.segmentation.filters.factory import create_filter, create_filter_by_sequence
from vpt.segmentation.utils.polygon_utils import get_polygons_from_mask, get_upscale_matrix


def test_empty() -> None:
    f = create_filter_by_sequence([])
    tmp = np.ones((1, 1), dtype=np.uint16)
    assert f is not None
    assert f(tmp)[0, 0] == 1
    f = create_filter_by_sequence(None)
    assert f is not None
    assert f(tmp)[0, 0] == 1


def test_invalid() -> None:
    with pytest.raises(NameError) as _:
        create_filter_by_sequence([Header("invalid", {'x': 1})])


def test_normalize() -> None:
    f = create_filter(Header('normalize', {}))
    assert f is not None
    tmp = np.zeros((16, 16), dtype=np.uint16)
    tmp[1, 1] = 100
    result = f(tmp)
    assert result.dtype == np.uint8
    assert result[1, 1] == 255 and result[0, 0] == 0


def test_blur() -> None:
    with pytest.raises(TypeError) as _:
        create_filter(Header('blur', {"type": "invalid"}))
    origin = np.zeros((5, 5), dtype=np.uint16)
    origin[2, 2] = 255
    f = create_filter(Header('blur', {"type": "median", "size": 3}))
    assert f is not None
    result = f(origin)
    assert result[2, 2] == 0
    f = create_filter(Header('blur', {"type": "gaussian", "size": 3}))
    assert f is not None
    result = f(origin)
    assert result[1, 1] > 0
    f = create_filter(Header('blur', {"type": "average", "size": 3}))
    assert f is not None
    result = f(origin)
    assert result[2, 2] == 28


def test_downsample() -> None:
    for scale in range(1, 8):
        f = create_filter(Header('downsample', {"scale": scale}))
        assert f is not None
        origin = np.zeros((100, 100), dtype=np.uint16)
        polygon = shapely.geometry.Polygon([(15, 20), (30, 60), (20, 80), (40, 100), (90, 90), (90, 10), (60, 30),
                                            (35, 10)])
        cv2.fillPoly(origin, [np.array(polygon.exterior.xy).round().astype(np.int32).T], 1)
        result = f(origin)
        seg_res = get_polygons_from_mask((result != 0).astype("uint8"), 1, 1)
        seg_res.transform_geoms(get_upscale_matrix(scale, scale))
        upscaled = seg_res.get_z_geoms(0).tolist()
        assert len(upscaled) == 1
        upscaled = upscaled[0]
        assert polygon.symmetric_difference(upscaled).area < 100 * (scale * 2.3)
