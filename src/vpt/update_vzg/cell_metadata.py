import numpy as np
import pandas

from vpt.update_vzg.imageparams import ImageParams
from vpt.utils.general_data import extend_btr_by_fixed_str


class PointTransform:
    def __init__(self, imageParams: ImageParams):
        self._texture_width, self._texture_height = imageParams.textureSize
        self._t_m = imageParams.micronToPixelMatrix

    def make_transform(self, x, y) -> tuple:
        x_texture = x * self._t_m[0][0] + self._t_m[0][2]
        y_texture = y * self._t_m[1][1] + self._t_m[1][2]

        x_world = x_texture / self._texture_width
        y_world = (1.0 - y_texture / self._texture_height)

        return x_world, y_world


class CellMetadata:

    MAX_BYTE_ID = 40

    def __init__(self, metadataDF: pandas.DataFrame, imageParams: ImageParams = None):
        self._volume_np: np.array
        self._centroid_np: np.array
        self._id_l: np.chararray

        self._cells_count = 0
        self._load(metadataDF, imageParams)

    def _load(self, metadataDF, imageParams: ImageParams):
        metadataDF = metadataDF.sort_index()
        self._id_l = list(map(str, metadataDF.index.tolist()))
        self._cells_count = len(self._id_l)
        self._volume_np = metadataDF.loc[:, 'volume'].values.tolist()
        centersMicrons = metadataDF.loc[:, ['center_x', 'center_y']].values.tolist()

        if imageParams is not None:
            point_transform = PointTransform(imageParams)
            self._centroid_np = [point_transform.make_transform(coord[0], coord[1]) for coord in centersMicrons]

    def get_volume_array(self) -> np.array:
        return self._volume_np

    def get_names_array(self) -> np.array:
        return self._id_l

    def get_cell_metadata_array(self) -> bytearray:
        cell_metadata_btr = bytearray()
        for cell_idx in range(self._cells_count):
            extend_btr_by_fixed_str(cell_metadata_btr, self._id_l[cell_idx], self.MAX_BYTE_ID)
            cell_metadata_btr.extend(np.float32(self._volume_np[cell_idx]))

            cell_metadata_btr.extend(np.float32(self._centroid_np[cell_idx][0]))
            cell_metadata_btr.extend(np.float32(self._centroid_np[cell_idx][1]))

        # write
        output_btr = bytearray()
        output_btr.extend(np.uint32(self._cells_count))  # cell count
        output_btr.extend(np.uint32(self.MAX_BYTE_ID))  # Size in bytes of one name

        output_btr.extend(cell_metadata_btr)
        return output_btr
