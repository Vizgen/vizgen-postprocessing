from typing import Optional, List, Dict

from vpt_core.segmentation.fuse import PolygonParams
from vpt_core.segmentation.segmentation_item import SegmentationItem, intersection

from vpt.entity import Strategy
from vpt.entity.resolver_base import ResolverBase, RelatedSegmentationResults, ChildInfo


class ParentMustCoverChild(ResolverBase):
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
        if parent:
            if self.strategy == Strategy.RemoveChild:
                for info in children:
                    if info.coverage < 1:
                        target.children.remove(info.data.get_entity_id())
            elif self.strategy == Strategy.ShrinkChild:
                for info in children:
                    if info.coverage < 1:
                        child_updated = intersection(info.data, parent)
                        child_params = (
                            self.polygon_parameters.get(child_updated.get_entity_type(), PolygonParams())
                            if self.polygon_parameters
                            else PolygonParams()
                        )
                        self.process_updated_item(
                            target.children,
                            info.data.get_entity_id(),
                            child_updated,
                            parent,
                            child_params.min_final_area,
                        )
