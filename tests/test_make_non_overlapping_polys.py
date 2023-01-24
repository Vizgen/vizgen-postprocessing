from tests.base_case import BaseCase
from tests.segmentation_utils import assert_seg_equals, Square, from_shapes, from_shapes_3d, Rect
from vpt.segmentation.utils.seg_result import SegmentationResult
import pytest


class ResolveOverlapCase(BaseCase):
    def __init__(self, name: str, segmentation: SegmentationResult, result: SegmentationResult):
        super(ResolveOverlapCase, self).__init__(name)
        self.segmentation = segmentation
        self.result = result


Make_non_Overlapping_Cases = [
    ResolveOverlapCase(
        name='empty',
        segmentation=SegmentationResult(),
        result=SegmentationResult()
    ),
    ResolveOverlapCase(
        name='no_overlap',
        segmentation=from_shapes([Square(0, 0, 9), Square(10, 10, 9), Square(20, 20, 9), Square(30, 30, 9)]),
        result=from_shapes([Square(0, 0, 9), Square(10, 10, 9), Square(20, 20, 9), Square(30, 30, 9)])
    ),
    ResolveOverlapCase(
        name='no_overlap_3d',
        segmentation=from_shapes_3d([[Square(0, 0, 9), Square(10, 10, 9)], [Square(10, 10, 9), Square(0, 0, 9)]]),
        result=from_shapes_3d([[Square(0, 0, 9), Square(10, 10, 9)], [Square(10, 10, 9), Square(0, 0, 9)]]),
    ),
    ResolveOverlapCase(
        name='large overlap: eliminate',
        segmentation=from_shapes([Square(0, 0, 20), Square(-1, -1, 11)]),
        result=from_shapes([Square(0, 0, 20).union(Square(-1, -1, 11))])
    ),
    ResolveOverlapCase(
        name='large overlap 3d: eliminate',
        segmentation=from_shapes_3d([[Square(0, 0, 20), Square(1, 1, 20)], [Square(5, 5, 15), Square(5, 5, 10)]]),
        result=from_shapes_3d([[Square(0, 0, 20), Square(1, 1, 20)]])
    ),
    ResolveOverlapCase(
        name='small overlap: difference, buffer = 2',
        segmentation=from_shapes([Square(0, 0, 20), Square(10, 10, 15)]),
        result=from_shapes([Square(0, 0, 20).difference(Square(8, 8, 12)), Square(10, 10, 15)])
    ),
    ResolveOverlapCase(
        name='small overlap 3d: difference, buffer = 2',
        segmentation=from_shapes_3d([[Square(0, 0, 20), Square(1, 1, 20)], [Square(15, 15, 10), Square(15, 15, 10)]]),
        result=from_shapes_3d([
            [Square(0, 0, 20).difference(Square(13, 13, 14)), Square(1, 1, 20).difference(Square(13, 13, 14))],
            [Square(15, 15, 10), Square(15, 15, 10)]]),
    ),
    ResolveOverlapCase(
        name='multi overlap eliminate',
        segmentation=from_shapes([Square(0, 0, 10), Square(0, 5, 5), Square(5, 0, 5)]),
        result=from_shapes([Square(0, 0, 10)])
    ),
    ResolveOverlapCase(
        name='multi overlap difference, buffer 2',
        segmentation=from_shapes([Square(0, 0, 10), Square(9, 5, 9), Square(9, 0, 8)]),
        result=from_shapes([
            Rect(0, 0, 7, 10),
            Rect(9, 10, 9, 4),
            Square(9, 0, 8)
        ])
    )
]


@pytest.mark.parametrize('case', Make_non_Overlapping_Cases, ids=str)
def test_make_non_overlapping_polys(case: ResolveOverlapCase) -> None:
    case.segmentation.make_non_overlapping_polys(min_area=4)
    assert_seg_equals(case.segmentation, case.result, 1)
