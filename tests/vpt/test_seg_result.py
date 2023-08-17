import numpy as np
from shapely.geometry import MultiPolygon, Polygon
from vpt_core.segmentation.seg_result import SegmentationResult

from vpt.run_segmentation_on_tile.output_utils import get_entity_type_code, update_entity_id

pts1 = np.array([(0, 0), (1, 0), (0, 1)])
pts2 = pts1 + (10, 10)
pts3 = pts1 * 10
t1 = Polygon(pts1)
t2 = Polygon(pts2)
t3 = Polygon(pts3)


def gen_test_data() -> SegmentationResult:
    return SegmentationResult(
        list_data={
            SegmentationResult.detection_id_field: list(range(3)),
            SegmentationResult.z_index_field: [1, 1, 1],
            SegmentationResult.cell_id_field: list(range(3)),
            SegmentationResult.geometry_field: [
                MultiPolygon([t1]),
                MultiPolygon([t2]),
                MultiPolygon([t3]),
            ],
        },
        entity="cell",
    )


def test_update_colum() -> None:
    sr = gen_test_data()
    sr.update_column(SegmentationResult.z_index_field, lambda z: 0)
    assert sr.df[SegmentationResult.z_index_field].to_list() == [0, 0, 0]
    sr.update_column(SegmentationResult.cell_id_field, lambda id: 1000 + id)
    assert sr.df[SegmentationResult.cell_id_field].to_list() == [1000, 1001, 1002]


def test_update_geom() -> None:
    const_poly = Polygon([(0, 0), (10, 0), (10, 10)])

    sr = gen_test_data()
    sr.update_geometry(lambda x: const_poly)
    for mp in sr.df[SegmentationResult.geometry_field].to_list():
        assert mp == MultiPolygon([const_poly])


def test_translate_geoms() -> None:
    sr = gen_test_data()
    sr.translate_geoms(100, 200)

    assert sr.df[SegmentationResult.geometry_field].to_list() == [
        MultiPolygon([Polygon(pts1 + (100, 200))]),
        MultiPolygon([Polygon(pts2 + (100, 200))]),
        MultiPolygon([Polygon(pts3 + (100, 200))]),
    ]


def test_transform_geoms() -> None:
    sr = gen_test_data()
    sr.transform_geoms(np.array([[2, 0, 10], [0, 3, -10], [0, 0, 1]]))

    assert sr.df[SegmentationResult.geometry_field].to_list() == [
        MultiPolygon([Polygon(pts1 * (2, 3) + (10, -10))]),
        MultiPolygon([Polygon(pts2 * (2, 3) + (10, -10))]),
        MultiPolygon([Polygon(pts3 * (2, 3) + (10, -10))]),
    ]


def test_entity_id_generation() -> None:
    sr = gen_test_data()
    sr.update_column(SegmentationResult.cell_id_field, lambda x: int(f"89{(x + 10) ** 4}"))
    source_ids = sr.df[sr.cell_id_field].to_list()

    sr.update_column(
        SegmentationResult.cell_id_field,
        update_entity_id,
        tile="8834",
        time="43049737",
        entity_type=get_entity_type_code(sr.entity_type),
    )
    assert sr.df[sr.cell_id_field].to_list() == [int(f"430498378834{i}") for i in source_ids]


def test_entity_id_overflow() -> None:
    sr = gen_test_data()
    sr.update_column(SegmentationResult.cell_id_field, lambda x: int(f"89{(x + 10) ** 5}"))

    try:
        sr.update_column(
            SegmentationResult.cell_id_field,
            update_entity_id,
            tile="8834",
            time="43049737",
            entity_type=get_entity_type_code(sr.entity_type),
        )
        assert False
    except Exception:
        return
