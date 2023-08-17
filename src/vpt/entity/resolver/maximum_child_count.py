from typing import Optional, List

from vpt_core.segmentation.segmentation_item import SegmentationItem

from vpt.entity.resolver_base import ResolverBase, RelatedSegmentationResults, ChildInfo
from vpt.entity import Strategy


class MaximumChildCount(ResolverBase):
    def __init__(self, strategy: Strategy, count: int):
        if strategy not in [Strategy.RemoveChild, Strategy.RemoveParent]:
            raise ValueError("Invalid strategy")
        self.strategy = strategy
        self.count = count

    def resolve(
        self,
        target: RelatedSegmentationResults,
        parent: Optional[SegmentationItem],
        children: List[ChildInfo],
    ) -> None:
        count = len(children)
        if parent and count > self.count:
            if self.strategy == Strategy.RemoveChild:
                indices = list(range(count))
                indices.sort(key=lambda x: children[x].data.get_volume() * children[x].coverage)
                for ind in indices[: -self.count]:
                    target.children.remove(children[ind].data.get_entity_id())
            elif self.strategy == Strategy.RemoveParent:
                target.parents.remove(parent.get_entity_id())
                for info in children:
                    target.children.update(info.data)
