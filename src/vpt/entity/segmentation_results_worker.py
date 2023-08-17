from typing import Optional, List

from geopandas import GeoDataFrame

from vpt_core.segmentation.seg_result import SegmentationResult
from vpt_core.segmentation.segmentation_item import SegmentationItem

from vpt.entity.resolver_base import StorageWorkerBase, RelatedSegmentationResults


class SegmentationResultsWorker(StorageWorkerBase):
    data: SegmentationResult

    def __init__(self, data: SegmentationResult):
        self.data = data

    def update(self, item: SegmentationItem, parent: Optional[SegmentationItem] = None) -> None:
        update_item = _update_with_parent(item, parent)
        self.data.update_item(update_item)

    def create(self, item: SegmentationItem, parent: Optional[SegmentationItem] = None) -> SegmentationItem:
        add_item = _update_with_parent(item, parent)
        item_id = self.data.add_item(add_item)
        return self.data.item(item_id)

    def remove(self, item_id: int) -> None:
        self.data.df.drop(self.data.df.loc[self.data.df[self.data.cell_id_field] == item_id].index, inplace=True)
        if hasattr(self, "on_remove"):
            self.on_remove(item_id)

    def parent_removed(self, parent_ids: List[int]) -> GeoDataFrame:
        rows = self.data.df[SegmentationResult.parent_id_field].isin(parent_ids)
        if any(rows):
            self.data.df.loc[rows, SegmentationResult.parent_id_field] = None
            self.data.df.loc[rows, SegmentationResult.parent_entity_field] = None
        return self.data.df[rows]


def create_segmentation_results_relation(
    parent_seg: SegmentationResult, child_seg: SegmentationResult, coverage_threshold: float = 0.5
) -> RelatedSegmentationResults:
    children = SegmentationResultsWorker(child_seg)
    parents = SegmentationResultsWorker(parent_seg)

    def on_remove(item_id: int):
        changed_seg = children.parent_removed([item_id])
        if len(changed_seg) == 0:
            return
        rows_seg = SegmentationResult(dataframe=changed_seg)
        rows_seg.set_entity_type(child_seg.entity_type)
        rows_seg.create_relationships(parent_seg, coverage_threshold)
        for item_id, item_df in rows_seg.df.groupby(SegmentationResult.cell_id_field):
            child_seg.update_item(SegmentationItem(child_seg.entity_type, item_df))

    def on_update_connected(item_ids: List[int]):
        changed_child_df = children.parent_removed(item_ids)
        if len(changed_child_df) == 0:
            return
        updated_parents = parent_seg.df[parent_seg.df[SegmentationResult.cell_id_field].isin(item_ids)]

        cur_child_seg = SegmentationResult(dataframe=changed_child_df)
        updated_parent_seg = SegmentationResult(dataframe=updated_parents)

        cur_child_seg.set_entity_type(child_seg.entity_type)
        updated_parent_seg.set_entity_type(parent_seg.entity_type)

        cur_child_seg.create_relationships(updated_parent_seg, coverage_threshold)
        for item_id, item_df in cur_child_seg.df.groupby(SegmentationResult.cell_id_field):
            child_seg.update_item(SegmentationItem(child_seg.entity_type, item_df))

    setattr(parents, "on_remove", on_remove)
    setattr(parents, "on_update_connected", on_update_connected)

    return RelatedSegmentationResults(parents, children)


def _update_with_parent(item: SegmentationItem, parent: Optional[SegmentationItem]):
    result = item.as_copy()
    parent_id, parent_type = None, None
    if parent is not None:
        parent_id = parent.get_entity_id()
        parent_type = parent.get_entity_type()
    result.set_parent(parent_type, parent_id)
    return result
