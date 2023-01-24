import pytest
from tests import IMAGES_ROOT
import numpy as np
from vpt.run_segmentation_on_tile.image import read_tile, ImageSet


def test_image_set() -> None:
    image = IMAGES_ROOT / 'mosaic_DAPI_z0.tif'
    data = ImageSet()
    for ch in ['ch1', 'ch2', 'ch3']:
        stack = {}
        for z in [0, 1, 2, 3, 4]:
            stack[z] = read_tile((z * 10, z * 10, 10, 10), str(image))
        data[ch] = stack
    assert len(data.z_levels()) == 5
    assert len(data.as_list('ch5')) == 0
    assert len(data.as_list('ch1')) == 5
    assert data.as_stack().shape == (5, 10, 10, 3)


def test_image_set_order() -> None:
    data = ImageSet()
    for ch, k in [('ch_1', 1), ('ch_10', 10), ('ch_20', 20)]:
        data[ch] = {}
        for z in [0, 1, 2, 3, 4]:
            data[ch][z] = np.ones((10, 10), dtype=np.uint16) * k

    with pytest.raises(Exception):
        data.as_stack(['invalid'])

    with pytest.raises(Exception):
        data.as_stack(['ch_1', 1])

    stack = data.as_stack(['ch_1', 'ch_10'])
    assert stack.shape == (5, 10, 10, 2)
    assert np.array_equal(stack[0, 0, 0], [1, 10])

    stack = data.as_stack(['ch_20', 'ch_1'])
    assert stack.shape == (5, 10, 10, 2)
    assert np.array_equal(stack[1, 1, 1], [20, 1])

    stack = data.as_stack(['ch_20', 'ch_10', 'ch_1'])
    assert stack.shape == (5, 10, 10, 3)
    assert np.array_equal(stack[2, 2, 2], [20, 10, 1])
