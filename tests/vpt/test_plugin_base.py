from vpt_core.segmentation.seg_result import SegmentationResult

from vpt.segmentation.segmentations_factory import get_seg_implementation


def test_empty_segmentation_method():
    seg = get_seg_implementation("non_exist")
    gt = SegmentationResult()
    res = seg.run_segmentation(
        segmentation_properties={}, segmentation_parameters={}, polygon_parameters={}, result=["own"], images={}
    )
    assert all(gt.df == res.df)


def test_empty_segmentation_validation():
    seg = get_seg_implementation("non_exist")
    task = {"f": 5}
    assert task == seg.validate_task(task)
