from typing import List

import pytest
from shapely.geometry import MultiPolygon

from tests.base_case import BaseCase
from tests.segmentation_utils import assert_seg_equals, Square, Rect, from_shapes_3d
from vpt.segmentation.utils.fuse import fuse_task_polygons, SegFusion
from vpt.run_segmentation_on_tile.main import reindex_by_task
from vpt.segmentation.utils.seg_result import SegmentationResult


class ZFusionCase(BaseCase):

    def __init__(self, name: str, seg_result: SegmentationResult, min_distance_between_entities: int,
                 min_final_area: int, result: SegmentationResult):
        super(ZFusionCase, self).__init__(name)

        self.seg_result = seg_result
        self.min_distance_between_entities = min_distance_between_entities
        self.min_final_area = min_final_area

        self.result = result


class TasksFusionCase(BaseCase):

    def __init__(self, name: str, seg_results: List[SegmentationResult], fusion_parameters: SegFusion,
                 result: SegmentationResult):
        super(TasksFusionCase, self).__init__(name)

        self.seg_results = seg_results
        self.fusion_parameters = fusion_parameters
        self.result = result


FUSE_Z_CASES = [
    ZFusionCase(
        name='no conflicts',
        seg_result=SegmentationResult(list_data={
            SegmentationResult.detection_id_field: list(range(11)),
            SegmentationResult.z_index_field: [0, 0, 0, 0, 1, 1, 1, 2, 2, 2, 2],
            SegmentationResult.cell_id_field: [0, 1, 2, 3, 0, 1, 2, 0, 1, 2, 3],
            SegmentationResult.geometry_field: [
                MultiPolygon([([(1, 3), (0.5, 4.5), (1.5, 5.3), (3.4, 4.2)], [])]),
                MultiPolygon([([(1.7, 1), (2.1, 2.3), (3.9, 2), (3.5, 1)], [])]),
                MultiPolygon([([(5, 1.7), (6.5, 2.5), (5.2, 0.4)], [])]),
                MultiPolygon([([(5.2, 3.7), (6, 4.9), (8, 5.5), (8, 2)], [])]),
                MultiPolygon([([(3.2, 2.5), (3.2, 3.4), (4.4, 3.7), (4.5, 2.5)], [])]),
                MultiPolygon([([(0.8, 2.8), (0.5, 4), (2, 5.4), (4, 4)], [])]),
                MultiPolygon([([(5, 3.5), (5.9, 5), (7.7, 5.5), (7.3, 2)], [])]),
                MultiPolygon([([(0.5, 2.5), (0.9, 4), (2, 5), (3.5, 4.2)], [])]),
                MultiPolygon([([(5.6, 3.5), (6.2, 5), (7.8, 5.5), (7.7, 2.5)], [])]),
                MultiPolygon([([(3, 2.3), (3.1, 3.4), (4.6, 4), (4.7, 2.3)], [])]),
                MultiPolygon([([(1.2, 0.9), (1.6, 2), (4, 2), (3.5, 0.8)], [])])
            ],
        }),
        min_distance_between_entities=1,
        min_final_area=500,
        result=SegmentationResult(list_data={
            SegmentationResult.detection_id_field: list(range(11)),
            SegmentationResult.z_index_field: [0, 0, 0, 0, 1, 1, 1, 2, 2, 2, 2],
            SegmentationResult.cell_id_field: [0, 1, 2, 3, 4, 0, 3, 0, 3, 4, 5],
            SegmentationResult.geometry_field: [
                MultiPolygon([([(1, 3), (0.5, 4.5), (1.5, 5.3), (3.4, 4.2)], [])]),
                MultiPolygon([([(1.7, 1), (2.1, 2.3), (3.9, 2), (3.5, 1)], [])]),
                MultiPolygon([([(5, 1.7), (6.5, 2.5), (5.2, 0.4)], [])]),
                MultiPolygon([([(5.2, 3.7), (6, 4.9), (8, 5.5), (8, 2)], [])]),
                MultiPolygon([([(3.2, 2.5), (3.2, 3.4), (4.4, 3.7), (4.5, 2.5)], [])]),
                MultiPolygon([([(0.8, 2.8), (0.5, 4), (2, 5.4), (4, 4)], [])]),
                MultiPolygon([([(5, 3.5), (5.9, 5), (7.7, 5.5), (7.3, 2)], [])]),
                MultiPolygon([([(0.5, 2.5), (0.9, 4), (2, 5), (3.5, 4.2)], [])]),
                MultiPolygon([([(5.6, 3.5), (6.2, 5), (7.8, 5.5), (7.7, 2.5)], [])]),
                MultiPolygon([([(3, 2.3), (3.1, 3.4), (4.6, 4), (4.7, 2.3)], [])]),
                MultiPolygon([([(1.2, 0.9), (1.6, 2), (4, 2), (3.5, 0.8)], [])])
            ]
        })
    ),
    ZFusionCase(
        name='with conflicts',
        seg_result=SegmentationResult(list_data={
            SegmentationResult.detection_id_field: list(range(12)),
            SegmentationResult.z_index_field: [0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2],
            SegmentationResult.cell_id_field: [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3],
            SegmentationResult.geometry_field: [
                MultiPolygon([([(1, 3), (0.5, 4.5), (1.5, 5.3), (3.4, 4.2)], [])]),
                MultiPolygon([([(1.7, 1), (2.1, 2.3), (3.9, 2), (3.5, 1)], [])]),
                MultiPolygon([([(5, 1.7), (6.5, 2.5), (5.2, 0.4)], [])]),
                MultiPolygon([([(5.2, 3.7), (6, 4.9), (8, 5.5), (8, 2)], [])]),
                MultiPolygon([([(3.2, 2.5), (3.2, 3.4), (4.4, 3.7), (4.5, 2.5)], [])]),
                MultiPolygon([([(0.8, 2.8), (0.5, 4), (2, 5.4), (4, 4)], [])]),
                MultiPolygon([([(5, 3.5), (5.9, 5), (7.7, 5.5), (7.3, 2)], [])]),
                MultiPolygon([([(2, 3.9), (2, 3), (3.5, 4), (3.5, 5)], [])]),
                MultiPolygon([([(0.5, 2.5), (0.9, 4), (2, 5), (3.5, 4.2)], [])]),
                MultiPolygon([([(5.6, 3.5), (6.2, 5), (7.8, 5.5), (7.7, 2.5)], [])]),
                MultiPolygon([([(3, 2.3), (3.1, 3.4), (4.6, 4), (4.7, 2.3)], [])]),
                MultiPolygon([([(1.2, 0.9), (1.6, 2), (4, 2), (3.5, 0.8)], [])])
            ],
        }),
        min_distance_between_entities=1,
        min_final_area=500,
        result=SegmentationResult(list_data={
            SegmentationResult.detection_id_field: list(range(12)),
            SegmentationResult.z_index_field: [0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2],
            SegmentationResult.cell_id_field: [0, 1, 2, 3, 4, 0, 3, 5, 0, 3, 4, 6],
            SegmentationResult.geometry_field: [
                MultiPolygon([([(1, 3), (0.5, 4.5), (1.5, 5.3), (3.4, 4.2)], [])]),
                MultiPolygon([([(1.7, 1), (2.1, 2.3), (3.9, 2), (3.5, 1)], [])]),
                MultiPolygon([([(5, 1.7), (6.5, 2.5), (5.2, 0.4)], [])]),
                MultiPolygon([([(5.2, 3.7), (6, 4.9), (8, 5.5), (8, 2)], [])]),
                MultiPolygon([([(3.2, 2.5), (3.2, 3.4), (4.4, 3.7), (4.5, 2.5)], [])]),
                MultiPolygon([([(0.8, 2.8), (0.5, 4), (2, 5.4), (2.3, 4.1)], [])]),
                MultiPolygon([([(5, 3.5), (5.9, 5), (7.7, 5.5), (7.3, 2)], [])]),
                MultiPolygon([([(2, 3.9), (2, 3), (3.5, 4), (3.5, 5)], [])]),
                MultiPolygon([([(0.5, 2.5), (0.9, 4), (2, 5), (2.5, 4)], [])]),
                MultiPolygon([([(5.6, 3.5), (6.2, 5), (7.8, 5.5), (7.7, 2.5)], [])]),
                MultiPolygon([([(3, 2.3), (3.1, 3.4), (4.6, 4), (4.7, 2.3)], [])]),
                MultiPolygon([([(1.2, 0.9), (1.6, 2), (4, 2), (3.5, 0.8)], [])])
            ]
        })
    )
]

FUSE_TASKS_CASES = [
    TasksFusionCase(
        name='2d_same_z_no_overlap',
        seg_results=[
            from_shapes_3d([[Square(0, 0, 10)], [Square(15, 15, 10)]]),
            from_shapes_3d([[Square(15, 0, 10)], [Square(0, 15, 10)]]),
        ],
        fusion_parameters=SegFusion('harmonize', {'min_distance_between_entities': 1, 'min_final_area': 5}),
        result=from_shapes_3d([[Square(0, 0, 10)], [Square(15, 15, 10)], [Square(15, 0, 10)], [Square(0, 15, 10)]],
                              cids=[100000, 100001, 200000, 200001])
    ),
    TasksFusionCase(
        name='2d_same_z_overlap',
        seg_results=[
            from_shapes_3d([[Square(0, 0, 10)], [Square(20, 0, 10)], [Square(40, 0, 10)]]),
            from_shapes_3d([[Square(1, 1, 8)], [Square(19, -1, 12)]]),
            from_shapes_3d([[Square(42, 0, 10)]]),
        ],
        fusion_parameters=SegFusion('harmonize', {'min_distance_between_entities': 1, 'min_final_area': 5}),
        result=from_shapes_3d([[Square(0, 0, 10)], [Rect(40, 0, 12, 10)], [Square(19, -1, 12)]],
                              cids=[100000, 100002, 200001])
    ),
    TasksFusionCase(
        name='2d_different_z',  # todo: replace this test with something we can read
        seg_results=[
            SegmentationResult(list_data={
                SegmentationResult.detection_id_field: list(range(7)),
                SegmentationResult.z_index_field: [0, 0, 0, 2, 4, 4, 4],
                SegmentationResult.cell_id_field: [0, 1, 3, 2, 0, 1, 3],
                SegmentationResult.geometry_field: [
                    MultiPolygon([([(9, 80), (13, 110), (49, 119), (40, 85)], [])]),
                    MultiPolygon([([(14, 35), (40, 58), (43, 24)], [])]),
                    MultiPolygon([([(120, 80), (105, 110), (128, 121), (144, 90)], [])]),
                    MultiPolygon([([(100, 18), (110, 59), (147, 6)], [])]),
                    MultiPolygon([([(16, 74), (24, 108), (59, 110), (43, 74)], [])]),
                    MultiPolygon([([(25, 20), (19, 50), (56, 50), (54, 19)], [])]),
                    MultiPolygon([([(104, 83), (117, 122), (150, 102)], [])])
                ],
            }, entity='cell'),
            SegmentationResult(list_data={
                SegmentationResult.detection_id_field: list(range(4)),
                SegmentationResult.z_index_field: [0, 2, 2, 2],
                SegmentationResult.cell_id_field: [0, 0, 1, 3],
                SegmentationResult.geometry_field: [
                    MultiPolygon([([(21, 42), (19, 66), (67, 69), (66, 41)], [])]),
                    MultiPolygon([([(40, 90), (40, 110), (81, 111), (81, 90)], [])]),
                    MultiPolygon([([(30, 34), (32, 61), (77, 60), (73, 30)], [])]),
                    MultiPolygon([([(92, 91), (93, 109), (135, 112), (131, 90)], [])])
                ],
            }, entity='cell'),
            SegmentationResult(list_data={
                SegmentationResult.detection_id_field: list(range(6)),
                SegmentationResult.z_index_field: [0, 0, 0, 2, 2, 4],
                SegmentationResult.cell_id_field: [0, 1, 3, 0, 1, 3],
                SegmentationResult.geometry_field: [
                    MultiPolygon([([(20, 90), (20, 100), (30, 100), (30, 90)], [])]),
                    MultiPolygon([([(43, 48), (43, 57), (55, 58), (55, 48)], [])]),
                    MultiPolygon([([(106, 97), (108, 106), (132, 106), (132, 99)], [])]),
                    MultiPolygon([([(56, 95), (57, 103), (70, 104), (69, 96)], [])]),
                    MultiPolygon([([(50, 41), (48, 54), (65, 53), (66, 41)], [])]),
                    MultiPolygon([([(128, 99), (139, 105), (142, 96), (131, 90)], [])])
                ],
            }, entity='cell')
        ],
        fusion_parameters=SegFusion('harmonize', {'min_distance_between_entities': 1, 'min_final_area': 5}),
        result=SegmentationResult(list_data={
            SegmentationResult.detection_id_field: list(range(11)),
            SegmentationResult.z_index_field: [0, 0, 0, 0, 2, 2, 2, 2, 4, 4, 4],
            SegmentationResult.cell_id_field: [100000, 100001, 100003, 200000, 100002, 200000, 200001, 200003, 100000,
                                               100001, 100003],
            SegmentationResult.geometry_field: [
                MultiPolygon([([(9, 80), (13, 110), (49, 119), (40, 85)], [])]),
                MultiPolygon([([(14, 35), (40, 58), (43, 24)], [])]),
                MultiPolygon([([(120, 80), (112, 98), (106, 97), (107, 107), (105, 110), (128, 121), (144, 90)], [])]),
                MultiPolygon([([(21, 42), (19, 66), (67, 69), (66, 41), (43, 41), (40, 58)], [])]),
                MultiPolygon([([(100, 18), (110, 59), (147, 6)], [])]),
                MultiPolygon([([(40, 90), (40, 110), (81, 111), (81, 90)], [])]),
                MultiPolygon([([(30, 34), (32, 61), (77, 60), (73, 30)], [])]),
                MultiPolygon([([(92, 91), (93, 109), (135, 112), (131, 90)], [])]),
                MultiPolygon([([(16, 74), (24, 108), (59, 110), (43, 74)], [])]),
                MultiPolygon([([(25, 20), (19, 50), (56, 50), (54, 19)], [])]),
                MultiPolygon([([(141, 99), (142, 96), (131, 90), (130, 93), (104, 83), (117, 122), (150, 102)], [])])
            ]
        }, entity='cell')
    ),
    TasksFusionCase(
        name='3d_two_cells_union',
        seg_results=[
            SegmentationResult(list_data={
                SegmentationResult.detection_id_field: list(range(3)),
                SegmentationResult.z_index_field: [0, 1, 2],
                SegmentationResult.cell_id_field: [0, 0, 0],
                SegmentationResult.geometry_field: [
                    MultiPolygon([([(10, 40), (9, 70), (49, 71), (51, 40)], [])]),
                    MultiPolygon([([(15, 35), (15, 66), (56, 66), (58, 35)], [])]),
                    MultiPolygon([([(20, 28), (17, 77), (43, 79), (50, 30)], [])])
                ],
            }, entity='cell'),
            SegmentationResult(list_data={
                SegmentationResult.detection_id_field: list(range(3)),
                SegmentationResult.z_index_field: [0, 1, 2],
                SegmentationResult.cell_id_field: [0, 0, 0],
                SegmentationResult.geometry_field: [
                    MultiPolygon([([(25, 30), (23, 66), (70, 70), (70, 32)], [])]),
                    MultiPolygon([([(12, 36), (11, 68), (55, 70), (55, 39)], [])]),
                    MultiPolygon([([(30, 23), (30, 60), (75, 60), (75, 27)], [])])
                ],
            }, entity='cell'),
        ],
        fusion_parameters=SegFusion('harmonize', {'min_distance_between_entities': 1, 'min_final_area': 5}),
        result=SegmentationResult(list_data={
            SegmentationResult.detection_id_field: list(range(3)),
            SegmentationResult.z_index_field: [0, 1, 2],
            SegmentationResult.cell_id_field: [200000, 200000, 200000],
            SegmentationResult.geometry_field: [
                MultiPolygon([([(10, 40), (9, 70), (49, 71), (49, 68), (70, 70), (70, 32), (25, 30), (24, 40)],
                               [])]),
                MultiPolygon([([(12, 36), (11, 68), (55, 70), (55, 65), (56, 66), (58, 35), (15, 35), (15, 36)],
                               [])]),
                MultiPolygon([([(20, 28), (17, 77), (43, 79), (46, 60), (75, 60), (75, 27), (30, 23), (30, 30)],
                               [])])
            ],
        }, entity='cell')
    ),
    TasksFusionCase(
        name='3d_two_cells_sub',
        seg_results=[
            SegmentationResult(list_data={
                SegmentationResult.detection_id_field: list(range(3)),
                SegmentationResult.z_index_field: [0, 1, 2],
                SegmentationResult.cell_id_field: [0, 0, 0],
                SegmentationResult.geometry_field: [
                    MultiPolygon([([(10, 40), (9, 70), (49, 71), (51, 40)], [])]),
                    MultiPolygon([([(15, 35), (15, 66), (56, 66), (58, 35)], [])]),
                    MultiPolygon([([(20, 28), (17, 77), (43, 79), (50, 30)], [])])
                ],
            }, entity='cell'),
            SegmentationResult(list_data={
                SegmentationResult.detection_id_field: list(range(3)),
                SegmentationResult.z_index_field: [0, 1, 2],
                SegmentationResult.cell_id_field: [0, 0, 0],
                SegmentationResult.geometry_field: [
                    MultiPolygon([([(45, 30), (43, 66), (60, 70), (60, 32)], [])]),
                    MultiPolygon([([(37, 36), (36, 68), (60, 70), (60, 39)], [])]),
                    MultiPolygon([([(50, 23), (50, 60), (95, 60), (95, 27)], [])])
                ],
            }, entity='cell'),
        ],
        fusion_parameters=SegFusion('harmonize', {'min_distance_between_entities': 1, 'min_final_area': 5}),
        result=SegmentationResult(list_data={
            SegmentationResult.detection_id_field: list(range(6)),
            SegmentationResult.z_index_field: [0, 0, 1, 1, 2, 2],
            SegmentationResult.cell_id_field: [100000, 200000, 100000, 200000, 100000, 200000],
            SegmentationResult.geometry_field: [
                MultiPolygon([([(10, 40), (9, 70), (49, 71), (49, 67), (43, 66), (43, 40)], [])]),
                MultiPolygon([([(45, 30), (43, 66), (60, 70), (60, 32)], [])]),
                MultiPolygon([([(15, 35), (15, 66), (34, 66), (35, 35)], [])]),
                MultiPolygon([([(37, 36), (36, 68), (60, 70), (60, 39)], [])]),
                MultiPolygon([([(20, 28), (17, 77), (43, 79), (50, 30)], [])]),
                MultiPolygon([([(50, 23), (50, 60), (95, 60), (95, 27)], [])])
            ],
        }, entity='cell')
    )
]


@pytest.mark.parametrize('case', FUSE_Z_CASES, ids=str)
def test_z_line_fusion(case: ZFusionCase) -> None:
    case.seg_result.fuse_across_z({'min_distance_between_entities': case.min_distance_between_entities,
                                   'min_final_area': case.min_final_area})
    assert_seg_equals(case.seg_result, case.result)


@pytest.mark.parametrize('case', FUSE_TASKS_CASES, ids=str)
def test_tasks_fusion(case: TasksFusionCase) -> None:
    case.seg_results = reindex_by_task(case.seg_results, list(range(len(case.seg_results))))
    result = fuse_task_polygons(case.seg_results, case.fusion_parameters)[0]
    assert_seg_equals(result, case.result, 150)
