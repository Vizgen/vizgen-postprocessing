from typing import List, Optional

from vpt.entity.resolver_base import SegmentationItem, ResolverBase, RelatedSegmentationResults, ChildInfo


class EmptyResolver(ResolverBase):
    def resolve(
        self,
        target: RelatedSegmentationResults,
        parent: Optional[SegmentationItem],
        children: List[ChildInfo],
    ) -> None:
        pass
