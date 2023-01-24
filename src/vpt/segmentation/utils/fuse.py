from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict

from vpt.segmentation.utils.seg_result import SegmentationResult
import vpt.log as log

import warnings
from shapely.errors import ShapelyDeprecationWarning


@dataclass(frozen=True)
class SegFusion:
    entity_fusion_strategy: str
    fused_polygon_postprocessing_parameters: Dict = field(default_factory=lambda: {
        "min_final_area": 0,
        "min_distance_between_entities": 2})


def run_harmonization(segmentations: List[SegmentationResult], min_distance: int, min_area: int):
    segmentation: SegmentationResult = SegmentationResult.combine_segmentations(segmentations)
    segmentation.make_non_overlapping_polys(min_distance, min_area)
    return segmentation


def run_union_fusion(segmentations: List[SegmentationResult], min_distance: int, min_area: int):
    segmentation: SegmentationResult = SegmentationResult.combine_segmentations(segmentations)
    segmentation.union_intersections(min_distance, min_area)
    return segmentation


def run_larger_fusion(segmentations: List[SegmentationResult], min_distance: int, min_area: int):
    segmentation: SegmentationResult = SegmentationResult.combine_segmentations(segmentations)
    segmentation.larger_resolve_intersections(min_distance, min_area)
    return segmentation


class FusionCallbacks(Enum):
    HARMONIZE = ('harmonize', run_harmonization)
    LARGER = ('larger', run_larger_fusion)
    UNION = ('union', run_union_fusion)


def fuse_task_polygons(segmentation_results: List[SegmentationResult], fusion_parameters: SegFusion):
    log.info("fuse_task_polygons")
    warnings.filterwarnings('ignore', category=ShapelyDeprecationWarning)
    results = []
    tasks_entities = [res.entity_type for res in segmentation_results]
    parameters = fusion_parameters.fused_polygon_postprocessing_parameters
    strategy_key = fusion_parameters.entity_fusion_strategy.upper()
    if strategy_key not in FusionCallbacks.__members__:
        raise Exception("Invalid fusion strategy")

    for entity_type in set(tasks_entities):
        cur_results = [seg_res for i, seg_res in enumerate(segmentation_results) if tasks_entities[i] == entity_type]
        if len(cur_results) <= 1:
            results.append(cur_results[0])
            continue
        seg_result = FusionCallbacks[strategy_key].value[1](cur_results, parameters['min_distance_between_entities'],
                                                            parameters['min_final_area'])
        seg_result.set_entity_type(entity_type)
        results.append(seg_result)

    return results
