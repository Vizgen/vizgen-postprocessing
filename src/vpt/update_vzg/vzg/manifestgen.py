import datetime

import numpy as np

from vpt.utils.general_data import grid_size_calculate

version_d = {"Major": 1, "Minor": 0, "Patch": 9}


class ManifestGenerator:
    """Generate dataset xml manifest."""

    version = "".join([str(version_d["Major"]), ".", str(version_d["Minor"]), ".", str(version_d["Patch"])])

    def __init__(self, textureSize, transformMatrix, dataSetName: str):
        self.generalInfo = {
            "Name": dataSetName,
            "Version": ManifestGenerator.version,
            "Created": -1,
            "PlanesCount": -1,
            "Bbox": {},
            "VoxelGridSize": {},
        }
        self._bBoxInfoDict = {
            "MinX": -1,
            "MinY": -1,
            "MaxX": -1,
            "MaxY": -1,
        }
        self._set_spatial_bbox(textureSize[0], textureSize[1], transformMatrix)

        self._gridSize = grid_size_calculate(textureSize, transformMatrix)

    def set_planes_count(self, planesCount: int):
        """Set planes count for current dataset."""
        self.generalInfo["PlanesCount"] = planesCount

    def _set_spatial_bbox(self, textureWidth, textureHeight, transformMatrix):
        self._bBoxInfoDict["MinX"] = np.float64(-transformMatrix[0][2] / transformMatrix[0][0])
        self._bBoxInfoDict["MinY"] = np.float64(-transformMatrix[1][2] / transformMatrix[1][1])
        self._bBoxInfoDict["MaxX"] = (textureWidth - transformMatrix[0][2]) / transformMatrix[0][0]
        self._bBoxInfoDict["MaxY"] = (textureHeight - transformMatrix[1][2]) / transformMatrix[1][1]

    def set_cells_status(self, cellsStatus: bool):
        self.generalInfo["Cells"] = cellsStatus

    def set_transcripts_status(self, transcriptsStatus: bool):
        self.generalInfo["Transcripts"] = transcriptsStatus

    def set_image_dict(self, imageDict: dict):
        """
        Args:
            imageDict: Dictionary  with required fields for images information.
        """
        self.generalInfo["Images"] = imageDict

    def create_json_manifest(self):
        """Runs conveyor that creates json manifest.

        Returns:
            json object.
        """
        self.generalInfo["Created"] = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()

        self.generalInfo["Bbox"] = self._bBoxInfoDict

        self.generalInfo["VoxelGridSize"] = {"Width": self._gridSize[0], "Height": self._gridSize[1]}

        return self.generalInfo
