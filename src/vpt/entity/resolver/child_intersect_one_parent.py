from typing import Optional, List, Dict

from vpt_core.segmentation.fuse import PolygonParams
from vpt_core.segmentation.segmentation_item import SegmentationItem, difference

from vpt.entity import Strategy
from vpt.entity.resolver_base import ResolverBase, RelatedSegmentationResults, ChildInfo


class ChildIntersectOneParent(ResolverBase):
    def __init__(self, strategy: Strategy, polygon_parameters: Optional[Dict[str, PolygonParams]]):
        if strategy not in [Strategy.ShrinkChild, Strategy.RemoveChild]:
            raise ValueError("Invalid strategy")
        self.strategy = strategy
        self.polygon_parameters = polygon_parameters

    def resolve(
        self,
        target: RelatedSegmentationResults,
        parent: Optional[SegmentationItem],
        children: List[ChildInfo],
    ) -> None:
        if self.strategy == Strategy.RemoveChild:
            for info in children:
                unresolved_num = len(info.unresolved_hits)
                if (parent and unresolved_num > 0) or unresolved_num > 1:
                    target.children.remove(info.data.get_entity_id())
        elif self.strategy == Strategy.ShrinkChild:
            for info in children:
                child_updated = info.data
                child_params = (
                    self.polygon_parameters.get(child_updated.get_entity_type(), PolygonParams())
                    if self.polygon_parameters
                    else PolygonParams()
                )
                process_hits = info.unresolved_hits if parent else info.unresolved_hits[1:]
                for conflict in process_hits:
                    child_updated = difference(child_updated, conflict, child_params.min_distance_between_entities)
                self.process_updated_item(
                    target.children, info.data.get_entity_id(), child_updated, parent, child_params.min_final_area
                )
