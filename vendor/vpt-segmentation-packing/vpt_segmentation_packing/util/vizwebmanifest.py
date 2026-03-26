"""Module with Task for generate vizgen web manifest"""
import os.path
from datetime import datetime
from typing import Any, Dict, Optional, Union

from vpt_segmentation_packing.util.io import save_json_analysis_result


class VizWebManifestGenerator:
    """An analysis task that generate web manifest."""

    def __init__(self, datasetName: str, version: Optional[str] = None, manifest_name: str = "manifest"):
        self._datasetName = datasetName
        timeNow = datetime.now()
        self._manifestDict: Dict[str, Any] = {
            "name": self._datasetName,
            "created": timeNow.strftime("%d/%m/%Y %H:%M:%S"),
        }
        self._manifestName = manifest_name
        if version is not None:
            self._manifestDict["version"] = str(version)

    def add_parameter(self, tagName: str, tagValue: Union[str, int, float, list, dict, tuple]):
        self._manifestDict[tagName] = tagValue

    def to_dict(self) -> dict:
        return self._manifestDict

    def save_result(self, output_folder: str, subdirectory: str = ""):
        if subdirectory != "":
            self._manifestDict["name"] += f"_{subdirectory}"

        outPath = os.path.join(output_folder, subdirectory)
        save_json_analysis_result(self._manifestDict, resultName=self._manifestName, resultPath=outPath)
