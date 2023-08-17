from typing import Optional, List, Dict

from vpt_core.segmentation.fuse import PolygonParams
from vpt_core.segmentation.segmentation_item import SegmentationItem, difference

from vpt.entity import Strategy
from vpt.entity.resolver_base import ResolverBase, RelatedSegmentationResults, ChildInfo


class ChildMustHaveParent(ResolverBase):
    def __init__(self, strategy: Strategy, polygon_parameters: Optional[Dict[str, PolygonParams]]):
        if strategy not in [Strategy.RemoveChild, Strategy.CreateParent]:
            raise ValueError("Invalid strategy")
        self.strategy = strategy
        self.polygon_parameters = polygon_parameters

    def resolve(
        self,
        target: RelatedSegmentationResults,
        parent: Optional[SegmentationItem],
        children: List[ChildInfo],
    ) -> None:
        if len(children) > 0 and not parent:
            if self.strategy == Strategy.RemoveChild:
                for info in children:
                    target.children.remove(info.data.get_entity_id())
            elif self.strategy == Strategy.CreateParent:
                for info in children:
                    child = info.data
                    new_parent = target.parents.create(child.as_copy())
                    target.children.update(child, new_parent)
                    for intersected_parent in info.unresolved_hits:
                        parent_params = (
                            self.polygon_parameters.get(intersected_parent.get_entity_type(), PolygonParams())
                            if self.polygon_parameters
                            else PolygonParams()
                        )
                        intersected_updated = difference(
                            intersected_parent, new_parent, parent_params.min_distance_between_entities
                        )
                        self.process_updated_item(
                            target.parents,
                            intersected_parent.get_entity_id(),
                            intersected_updated,
                            min_area=parent_params.min_final_area,
                        )
