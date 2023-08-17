from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from vpt_core.segmentation.seg_result import SegmentationResult
from vpt_core.segmentation.segmentation_item import SegmentationItem


class StorageWorkerBase(ABC):
    @abstractmethod
    def update(self, item: SegmentationItem, parent: Optional[SegmentationItem] = None) -> None:
        pass

    @abstractmethod
    def create(self, item: SegmentationItem, parent: Optional[SegmentationItem] = None) -> SegmentationItem:
        pass

    @abstractmethod
    def remove(self, item_id: int) -> None:
        pass


@dataclass
class RelatedSegmentationResults:
    parents: StorageWorkerBase
    children: StorageWorkerBase


@dataclass
class ChildInfo:
    data: SegmentationItem
    coverage: float
    unresolved_hits: List[SegmentationItem]


class ResolverBase(ABC):
    @abstractmethod
    def resolve(
        self,
        target: RelatedSegmentationResults,
        parent: Optional[SegmentationItem],
        children: List[ChildInfo],
    ) -> None:
        pass

    @staticmethod
    def process_updated_item(
        storage: StorageWorkerBase,
        item_id: int,
        updated_item: SegmentationItem,
        parent: Optional[SegmentationItem] = None,
        min_area: float = 0,
    ):
        connected = SegmentationResult.get_connected_items(updated_item)
        if len(connected) == 0:
            storage.remove(item_id)
        else:
            connected = sorted(connected, key=lambda x: x.get_volume())
            storage.update(connected[-1], parent)
            for i, item in enumerate(connected[:-1]):
                if any(cell.area > min_area for cell in item.df[item.geometry_field]):
                    connected[i] = storage.create(item, parent)
            if len(connected) > 1 and hasattr(storage, "on_update_connected"):
                storage.on_update_connected([updated.get_entity_id() for updated in connected])
