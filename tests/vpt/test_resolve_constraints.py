from typing import List

import pytest

from vpt.entity import Constraint, Strategy
from vpt.entity.relationships import resolve_constraint
from vpt_core.segmentation.seg_result import SegmentationResult
from vpt_core.utils.base_case import BaseCase
from vpt_core.utils.segmentation_utils import assert_seg_equals, from_shapes, Square, Rect, from_shapes_3d


def x_bounded_rect(x_start, x_width):
    y_width = 10
    return Rect(x_start, 0, x_width, y_width)


def get_input_parent():
    return from_shapes(
        [Rect(5, 15, 12.5, 10), Rect(20, 20, 12.5, 10), Square(20, 0, 15)], cids=[20, 21, 22], entity_type="nuc"
    )


def get_input_child():
    return from_shapes(
        [
            Square(7.5, 22.5, 5),
            Square(27.5, 27.5, 5),
            Rect(5, 10, 5, 10),
            Rect(15, 20, 7, 5),
            Rect(15, 5, 7.5, 5),
            Rect(25, 5, 5, 10),
        ],
        cids=[10, 11, 12, 13, 14, 15],
    )


class TestResolveConstraintCase(BaseCase):
    def __init__(
        self,
        name: str,
        constraints: List[Constraint],
        parent_seg: SegmentationResult,
        child_seg: SegmentationResult,
        parent_res: SegmentationResult,
        child_res: SegmentationResult,
        child_coverage: float = 0.1,
    ):
        super(TestResolveConstraintCase, self).__init__(name)
        self.constraints = constraints
        self.parent_seg = parent_seg
        self.child_seg = child_seg
        self.parent_res = parent_res
        self.child_res = child_res
        self.child_coverage = child_coverage


TEST_CASES: List[TestResolveConstraintCase] = [
    TestResolveConstraintCase(
        name="one z, one constraint",
        constraints=[Constraint("maximum_child_count", 1, Strategy.RemoveChild)],
        parent_seg=get_input_parent(),
        child_seg=get_input_child(),
        parent_res=from_shapes(
            [Rect(5, 15, 12.5, 10), Rect(20, 20, 12.5, 10), Square(20, 0, 15)], cids=[20, 21, 22], entity_type="nuc"
        ),
        child_res=from_shapes([Square(27.5, 27.5, 5), Rect(5, 10, 5, 10), Rect(25, 5, 5, 10)], cids=[11, 12, 15]),
    ),
    TestResolveConstraintCase(
        name="one z, no child",
        constraints=[Constraint("minimum_child_count", 1, Strategy.CreateChild)],
        parent_seg=get_input_parent(),
        child_seg=from_shapes([]),
        parent_res=get_input_parent(),
        child_res=from_shapes([Rect(5, 15, 12.5, 10), Rect(20, 20, 12.5, 10), Square(20, 0, 15)]),
    ),
    TestResolveConstraintCase(
        name="one z, mincc cc with overlaps",
        constraints=[Constraint("minimum_child_count", 1, Strategy.CreateChild)],
        parent_seg=from_shapes([Square(10, 10, 15)]),
        child_seg=from_shapes([Square(15, 22, 8), Rect(10, 5, 5, 8)]),
        parent_res=from_shapes([Square(10, 10, 15)]),
        child_res=from_shapes([Rect(10, 7, 5, 3), Rect(15, 25, 10, 3), Square(10, 10, 15)]),
        child_coverage=0.5,
    ),
    TestResolveConstraintCase(
        name="one z, cmhp cp shrimping",
        constraints=[Constraint("child_must_have_parent", None, Strategy.CreateParent)],
        parent_seg=from_shapes([Rect(5, 0, 10, 13), Rect(5, 15, 10, 13)]),
        child_seg=from_shapes([Rect(5, 10, 15, 10)]),
        parent_res=from_shapes([Rect(5, 0, 10, 10), Rect(5, 20, 10, 8), Rect(5, 10, 15, 10)]),
        child_res=from_shapes([Rect(5, 10, 15, 10)]),
        child_coverage=0.5,
    ),
    TestResolveConstraintCase(
        name="one z, remove parent after difference",
        constraints=[Constraint("child_must_have_parent", None, Strategy.CreateParent)],
        parent_seg=from_shapes([Rect(5, 5, 5, 10), Rect(5, 17, 10, 8)]),
        child_seg=from_shapes([Rect(0, 3, 15, 17), Square(5, 5, 5)]),
        parent_res=from_shapes([Rect(0, 3, 15, 17), Rect(5, 20, 10, 5)], [2, 1]),
        child_res=from_shapes([Rect(0, 3, 15, 17), Square(5, 5, 5)]),
        child_coverage=0.5,
    ),
    TestResolveConstraintCase(
        name="one z, cmhp cp cell splitting",
        constraints=[Constraint("child_must_have_parent", None, Strategy.CreateParent)],
        parent_seg=from_shapes([Rect(10, 5, 10, 30)]),
        child_seg=from_shapes([Square(12, 7, 6), Rect(5, 15, 25, 5)]),
        parent_res=from_shapes([Rect(10, 20, 10, 15), Rect(5, 15, 25, 5), Rect(10, 5, 10, 10)]),
        child_res=from_shapes([Square(12, 7, 6), Rect(5, 15, 25, 5)]),
        child_coverage=0.5,
    ),
    TestResolveConstraintCase(
        name="one z, several constraints",
        constraints=[
            Constraint("child_intersect_one_parent", None, Strategy.ShrinkChild),
            Constraint("maximum_child_count", 2, Strategy.RemoveParent),
            Constraint("child_must_have_parent", None, Strategy.CreateParent),
        ],
        parent_seg=get_input_parent(),
        child_seg=get_input_child(),
        parent_res=from_shapes(
            [Rect(20, 20, 12.5, 10), Square(20, 0, 15), Square(7.5, 22.5, 5), Rect(5, 10, 5, 10), Square(15, 20, 5)],
            cids=[21, 22, 23, 24, 25],
            entity_type="nuc",
        ),
        child_res=from_shapes(
            [
                Square(7.5, 22.5, 5),
                Square(27.5, 27.5, 5),
                Square(5, 10, 5),
                Square(15, 20, 5),
                Rect(15, 5, 7.5, 5),
                Rect(25, 5, 5, 10),
            ],
            cids=[10, 11, 12, 13, 14, 15],
        ),
    ),
    TestResolveConstraintCase(
        name="multiple z, several constraints",
        constraints=[
            Constraint("child_intersect_one_parent", None, Strategy.ShrinkChild),
            Constraint("maximum_child_count", 1, Strategy.RemoveParent),
            Constraint("child_must_have_parent", None, Strategy.CreateParent),
            Constraint("parent_must_cover_child", None, Strategy.ShrinkChild),
        ],
        parent_seg=from_shapes_3d(
            [
                [x_bounded_rect(5, 15), x_bounded_rect(3, 19), x_bounded_rect(5, 20), x_bounded_rect(5, 15)],
                [x_bounded_rect(27, 11)],
                [x_bounded_rect(43, 17), x_bounded_rect(43, 17), x_bounded_rect(50, 10), x_bounded_rect(55, 5)],
            ],
            cids=[20, 20, 20, 20, 21, 22, 22, 22, 22],
            entity_type="cell",
        ),
        child_seg=from_shapes_3d(
            [
                [x_bounded_rect(15, 8), x_bounded_rect(15, 10), x_bounded_rect(15, 10), x_bounded_rect(20, 5)],
                [x_bounded_rect(35, 10), x_bounded_rect(35, 10), x_bounded_rect(35, 5), x_bounded_rect(35, 5)],
                [x_bounded_rect(47, 5), x_bounded_rect(47, 5)],
                [x_bounded_rect(55, 5), x_bounded_rect(55, 5), x_bounded_rect(55, 5), x_bounded_rect(55, 5)],
            ],
            cids=[10, 10, 10, 10, 11, 11, 11, 11, 12, 12, 13, 13, 13, 13],
            entity_type="nuc",
        ),
        parent_res=from_shapes_3d(
            [
                [x_bounded_rect(5, 15), x_bounded_rect(3, 19), x_bounded_rect(5, 20), x_bounded_rect(5, 15)],
                [x_bounded_rect(27, 11)],
                [x_bounded_rect(38, 5), x_bounded_rect(35, 10), x_bounded_rect(35, 5), x_bounded_rect(35, 5)],
                [x_bounded_rect(47, 5), x_bounded_rect(47, 5)],
                [x_bounded_rect(55, 5), x_bounded_rect(55, 5), x_bounded_rect(55, 5), x_bounded_rect(55, 5)],
            ],
            cids=[20, 20, 20, 20, 21, 22, 22, 22, 22, 23, 23, 24, 24, 24, 24],
            entity_type="cell",
        ),
        child_res=from_shapes_3d(
            [
                [x_bounded_rect(15, 5), x_bounded_rect(15, 7), x_bounded_rect(15, 10)],
                [x_bounded_rect(38, 5), x_bounded_rect(35, 10), x_bounded_rect(35, 5), x_bounded_rect(35, 5)],
                [x_bounded_rect(47, 5), x_bounded_rect(47, 5)],
                [x_bounded_rect(55, 5), x_bounded_rect(55, 5), x_bounded_rect(55, 5), x_bounded_rect(55, 5)],
            ],
            cids=[10, 10, 10, 11, 11, 11, 11, 12, 12, 13, 13, 13, 13],
            entity_type="nuc",
        ),
        child_coverage=0.5,
    ),
]


@pytest.mark.parametrize("case", TEST_CASES, ids=str)
def test_constraint(case: TestResolveConstraintCase):
    case.child_seg.create_relationships(case.parent_seg, case.child_coverage)
    child_res, parent_res = case.child_seg, case.parent_seg
    for constraint in case.constraints:
        child_res, parent_res = resolve_constraint(child_res, parent_res, constraint, case.child_coverage)

    case.child_res.create_relationships(case.parent_res, case.child_coverage)
    assert_seg_equals(child_res, case.child_res)
    assert_seg_equals(parent_res, case.parent_res)
