from typing import Callable, Dict

from vpt.run_segmentation_on_tile.image import ImageSet
from vpt.run_segmentation_on_tile.input_utils import SegTask

from vpt.segmentation.entity import parse_entity
from vpt.segmentation.utils.seg_result import SegmentationResult


def empty_validator(x: Dict) -> Dict:
    return x


def get_task_validator(segmentation_family: str) -> Callable[[Dict], Dict]:
    key = segmentation_family.upper()
    if key == 'CELLPOSE':
        from vpt.segmentation.cellpose.validate import validate_task as validate_cellpose_task
        return validate_cellpose_task
    if key == 'WATERSHED':
        from vpt.segmentation.watershed.validate import validate_task as validate_watershed_task
        return validate_watershed_task
    return empty_validator


def run_segmentation(image: ImageSet, task: SegTask) -> SegmentationResult:
    key = task.segmentation_family.upper()
    runner = None
    if key == 'CELLPOSE':
        from vpt.segmentation.cellpose.segmentation import run_segmentation as run_cellpose
        runner = run_cellpose
    if key == 'WATERSHED':
        from vpt.segmentation.watershed.segmentation import run_segmentation as run_watershed
        runner = run_watershed

    return runner(image, task.segmentation_properties, task.segmentation_parameters,
                  task.polygon_parameters, parse_entity(task.entity_types_detected))
