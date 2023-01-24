import cv2
import numpy as np
from shapely.geometry import Point

from tests import TEST_DATA_ROOT
from vpt.segmentation.stardist.seeds import StardistSeedsExtractor
from vpt.segmentation.watershed.segmentation import run_watershed, polygons_from_stardist
from vpt.segmentation.entity import Entity
from vpt.run_segmentation_on_tile.image import ImageSet

TEST_MODEL = str(TEST_DATA_ROOT / '2D_versatile_fluo')


def test_run_watershed() -> None:
    dapi = np.ones((256, 256), dtype=np.uint16)
    membrane = np.ones((256, 256), dtype=np.uint16)
    cv2.circle(dapi, (128, 128), 64, (255, 255, 255), -1)
    cv2.circle(membrane, (128, 128), 96, (255, 255, 255), -1)

    images = ImageSet()
    images['DAPI'] = {}
    images['DAPI'][0] = dapi
    images['DAPI'][1] = dapi

    images['PolyT'] = {}
    images['PolyT'][0] = membrane
    images['PolyT'][1] = membrane

    parameters = {
        'stardist_model': TEST_MODEL,
        'seed_channel': 'DAPI',
        'entity_fill_channel': 'PolyT'
    }

    nucs, cells = run_watershed(images, parameters, Entity.Cells)
    assert len(nucs[0]) == 1
    assert len(nucs[1]) == 1
    assert cells[0, 128, 128] == 1
    assert cells[1, 128, 128] == 1


def test_run_watershed_2() -> None:
    dapi = np.ones((256, 256), dtype=np.uint16)
    membrane = np.ones((256, 256), dtype=np.uint16)
    circles = [((64, 64), 30), ((196, 64), 20), ((64, 196), 10), ((196, 196), 5)]
    for center, r in circles:
        cv2.circle(dapi, center, r, (255, 255, 255), -1)
        cv2.circle(membrane, center, r + r, (255, 255, 255), -1)

    images = ImageSet()
    images['DAPI'] = {}
    images['DAPI'][0] = dapi
    images['DAPI'][1] = dapi
    images['DAPI'][2] = dapi

    images['PolyT'] = {}
    images['PolyT'][0] = membrane
    images['PolyT'][1] = membrane
    images['PolyT'][2] = membrane

    parameters = {
        'stardist_model': TEST_MODEL,
        'seed_channel': 'DAPI',
        'entity_fill_channel': 'PolyT'
    }

    nucs, cells = run_watershed(images, parameters, Entity.Cells)
    assert len(nucs) == 3
    assert len(nucs[0]) == 3 and len(nucs[1]) == 3 and len(nucs[2]) == 3
    for center, r in circles:
        for z in range(3):
            if r + r > 16:
                assert cells[z, center[0], center[1]] > 0
            else:
                assert cells[z, center[0], center[1]] == 0


def test_stardist_interop() -> None:
    dapi = np.ones((256, 256), dtype=np.uint16)
    cv2.circle(dapi, (128, 128), 32, (255, 255, 255), -1)
    cv2.circle(dapi, (64, 196), 64, (255, 255, 255), -1)
    extractor = StardistSeedsExtractor(TEST_MODEL)
    result = extractor.run_prediction(dapi)
    seg_result = polygons_from_stardist([result], {
        "simplification_tol": 2,
        "smoothing_radius": 3,
        "minimum_final_area": 100
    })
    polys = seg_result.get_z_geoms(0).tolist()
    polys.sort(key=lambda x: x.area)
    assert len(polys) == 2
    assert polys[0].contains(Point(128, 128))
    assert polys[1].contains(Point(64, 196))
    assert not polys[1].contains(Point(196, 64))
