from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

import pandas as pd

from vpt.entity import Constraint, constraint_from_dict, Strategy
from vpt.entity.factory import get_constraint_resolver
from vpt.entity.resolver_base import ChildInfo
from vpt.entity.segmentation_results_worker import create_segmentation_results_relation
from vpt_core import log
from vpt_core.segmentation.fuse import PolygonParams
from vpt_core.segmentation.seg_result import SegmentationResult
from vpt_core.segmentation.segmentation_item import SegmentationItem


@dataclass(frozen=True)
class EntityRelationships:
    parent_type: str
    child_type: str
    child_coverage_threshold: float
    constraints: List[Constraint]


def relationships_from_dict(raw_data: Dict) -> EntityRelationships:
    return EntityRelationships(
        parent_type=raw_data["parent_type"],
        child_type=raw_data["child_type"],
        child_coverage_threshold=float(raw_data["child_coverage_threshold"]),
        constraints=[constraint_from_dict(x) for x in raw_data["constraints"]],
    )


def get_default_relationship() -> EntityRelationships:
    max_child = Constraint("maximum_child_count", 3, Strategy.RemoveChild)
    min_child = Constraint("minimum_child_count", 1, Strategy.CreateChild)
    have_parent = Constraint("child_must_have_parent", None, Strategy.CreateParent)
    cover_child = Constraint("parent_must_cover_child", None, Strategy.ShrinkChild)
    intersect_one = Constraint("child_intersect_one_parent", None, Strategy.ShrinkChild)

    return EntityRelationships("cell", "nuclei", 0.5, [have_parent, cover_child, intersect_one, max_child, min_child])


def generate_child_info(child: SegmentationItem, parent_id: Optional[int], parent_res: SegmentationResult):
    overlapping_entities = SegmentationResult.find_overlapping_entities(parent_res.df, child.df)
    intersected_parents = [
        parent_res.item(intersected_id) for _, intersected_id in overlapping_entities if intersected_id != parent_id
    ]
    if parent_id is None:
        coverage = 0
    else:
        coverage = child.get_overlapping_volume(parent_res.item(parent_id)) / child.get_volume()
    return ChildInfo(child, coverage, intersected_parents)


def resolve_constraint(
    child_res: SegmentationResult,
    parent_res: SegmentationResult,
    constraint: Constraint,
    coverage_threshold: float,
    polygon_parameters: Optional[Dict[str, PolygonParams]] = None,
) -> Tuple[SegmentationResult, SegmentationResult]:
    log.info(
        f"resolving {constraint.constraint} started with parent segmentation of {len(parent_res.df)} detections and "
        f"child segmentation of {len(child_res.df)} detections"
    )
    resolver = get_constraint_resolver(constraint, polygon_parameters)
    target = create_segmentation_results_relation(parent_res, child_res, coverage_threshold)

    cell_field = SegmentationResult.cell_id_field
    parent_field = SegmentationResult.parent_id_field

    for parent_id, children_gdf in log.show_progress(child_res.df.groupby(parent_field)):
        parent_input = parent_res.item(parent_id)
        children_results = [child_res.item(child_id) for child_id in children_gdf[cell_field].unique()]
        child_infos = [generate_child_info(cur_child_res, parent_id, parent_res) for cur_child_res in children_results]
        resolver.resolve(target, parent_input, child_infos)

    # in no parent case process children items one by one
    no_parent_df = child_res.df[child_res.df[parent_field].isnull()]
    for child_id in log.show_progress(no_parent_df[cell_field].unique()):
        child_info = generate_child_info(child_res.item(child_id), None, parent_res)
        resolver.resolve(target, None, [child_info])

    # no child
    for parent_id in log.show_progress(set(parent_res.df[cell_field]).difference(child_res.df[parent_field])):
        cur_parent_input = parent_res.item(parent_id) if not pd.isnull(parent_id) else None
        resolver.resolve(target, cur_parent_input, [])

    parent_overlaps = parent_res.find_overlapping_entities(parent_res.df)
    child_overlaps = child_res.find_overlapping_entities(child_res.df)
    if len(parent_overlaps) > 0:
        log.warning(f"After constraint resolution found overlaps on parent seg: {parent_overlaps}")
    if len(child_overlaps) > 0:
        log.warning(f"After constraint resolution found overlaps on child seg: {child_overlaps}")
    return child_res, parent_res


def create_entity_relationships(
    segmentation_results: List[SegmentationResult],
    entity_type_relationships: Optional[EntityRelationships],
    polygon_parameters: Optional[Dict[str, PolygonParams]] = None,
) -> List[SegmentationResult]:
    if len(segmentation_results) < 2:
        return segmentation_results
    if entity_type_relationships is None:
        raise ValueError("Relationships are not specified")
    if len(segmentation_results) > 2:
        raise ValueError("More than two entity types are not supported")

    child_res, parent_res = None, None
    for i, seg_res in enumerate(segmentation_results):
        if seg_res.entity_type == entity_type_relationships.child_type:
            child_res = segmentation_results[i]
        elif seg_res.entity_type == entity_type_relationships.parent_type:
            parent_res = segmentation_results[i]
    if child_res is None or parent_res is None:
        raise ValueError("Detected results are not match relationships entity types")

    child_res.create_relationships(parent_res, entity_type_relationships.child_coverage_threshold)
    for constraint in entity_type_relationships.constraints:
        child_res, parent_res = resolve_constraint(
            child_res, parent_res, constraint, entity_type_relationships.child_coverage_threshold, polygon_parameters
        )

    return [child_res, parent_res]
