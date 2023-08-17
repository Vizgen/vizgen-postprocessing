from typing import Optional, Dict

from vpt.entity.empty_resolver import EmptyResolver
from vpt.entity.resolver.child_intersect_one_parent import ChildIntersectOneParent
from vpt.entity.resolver.child_must_have_parent import ChildMustHaveParent
from vpt.entity.resolver.minimum_child_count import MinimumChildCount
from vpt.entity.resolver.parent_must_cover_child import ParentMustCoverChild
from vpt.entity.resolver_base import ResolverBase
from vpt.entity import Constraint
from vpt.entity.resolver.maximum_child_count import MaximumChildCount
from vpt_core.segmentation.fuse import PolygonParams


def get_constraint_resolver(
    constraint: Constraint, polygon_parameters: Optional[Dict[str, PolygonParams]]
) -> ResolverBase:
    if constraint.constraint == "maximum_child_count":
        if constraint.value:
            return MaximumChildCount(constraint.resolution, constraint.value)
        else:
            raise ValueError("count must be defined")
    if constraint.constraint == "minimum_child_count":
        if constraint.value:
            return MinimumChildCount(constraint.resolution, constraint.value)
        else:
            raise ValueError("count must be defined")
    if constraint.constraint == "child_must_have_parent":
        return ChildMustHaveParent(constraint.resolution, polygon_parameters)
    if constraint.constraint == "parent_must_cover_child":
        return ParentMustCoverChild(constraint.resolution, polygon_parameters)
    if constraint.constraint == "child_intersect_one_parent":
        return ChildIntersectOneParent(constraint.resolution, polygon_parameters)

    return EmptyResolver()
