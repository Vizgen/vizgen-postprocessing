from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict


class Strategy(Enum):
    Unknown = ""
    RemoveChild = "remove_child"
    RemoveParent = "remove_parent"
    CreateParent = "create_parent"
    CreateChild = "create_child"
    ShrinkChild = "shrink_child"


@dataclass(frozen=True)
class Constraint:
    constraint: str
    value: Optional[int]
    resolution: Strategy


def constraint_from_dict(raw_data: Dict) -> Constraint:
    return Constraint(
        constraint=raw_data["constraint"],
        value=int(raw_data["value"]) if raw_data["value"] else None,
        resolution=Strategy(raw_data["resolution"]),
    )
