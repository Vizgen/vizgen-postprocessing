from typing import List, Optional

from vpt.entity.resolver_base import ChildInfo, RelatedSegmentationResults, ResolverBase, SegmentationItem


class EmptyResolver(ResolverBase):
    def resolve(
        self,
        target: RelatedSegmentationResults,
        parent: Optional[SegmentationItem],
        children: List[ChildInfo],
    ) -> None:
        pass
