from importlib import import_module
from typing import Dict, Iterable, List, Optional, Union

import pandas as pd
from vpt_core.io.image import ImageSet
from vpt_core.segmentation.seg_result import SegmentationResult
from vpt_core.segmentation.segmentation_base import SegmentationBase


class EmptySegmentation(SegmentationBase):
    @staticmethod
    def run_segmentation(
        segmentation_properties: Dict,
        segmentation_parameters: Dict,
        polygon_parameters: Dict,
        result: List[str],
        images: Optional[ImageSet] = None,
        transcripts: Optional[pd.DataFrame] = None,
    ) -> Union[SegmentationResult, Iterable[SegmentationResult]]:
        return SegmentationResult()

    @staticmethod
    def validate_task(task: Dict) -> Dict:
        return task


def get_seg_implementation(seg_name: str) -> SegmentationBase:
    package_name = f"vpt_plugin_{seg_name.lower()}"
    try:
        m = import_module(".segment", package=package_name)
        return getattr(m, "SegmentationMethod")
    except Exception:
        return EmptySegmentation()
