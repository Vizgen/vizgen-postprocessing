from typing import Optional, List

from vpt_core.segmentation.segmentation_item import SegmentationItem

from vpt.entity.resolver_base import ResolverBase, RelatedSegmentationResults, ChildInfo
from vpt.entity import Strategy


class MinimumChildCount(ResolverBase):
    def __init__(self, strategy: Strategy, count: int):
        if strategy not in [Strategy.CreateChild, Strategy.RemoveParent]:
            raise ValueError("Invalid strategy")
        if strategy == Strategy.CreateChild and count != 1:
            raise ValueError('Invalid count For "minimum child count" strategy')
        self.strategy = strategy
        self.count = count

    def resolve(
        self,
        target: RelatedSegmentationResults,
        parent: Optional[SegmentationItem],
        children: List[ChildInfo],
    ) -> None:
        count = len(children)
        if parent and count < self.count:
            parent_id = parent.get_entity_id()

            if self.strategy == Strategy.RemoveParent:
                target.parents.remove(parent_id)
                for info in children:
                    target.children.update(info.data)
            elif self.strategy == Strategy.CreateChild:
                new_child = parent.as_copy()
                target.children.create(new_child, parent)
