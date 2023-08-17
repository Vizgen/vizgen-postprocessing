from typing import List, Optional

import numpy as np
import pandas

from vpt.update_vzg.byte_utils import extend_with_u32, extend_with_f32
from vpt.update_vzg.imageparams import ImageParams
from vpt.utils.general_data import extend_btr_by_fixed_str


class PointTransform:
    def __init__(self, image_params: ImageParams):
        self._texture_width, self._texture_height = image_params.textureSize
        self._t_m = image_params.micronToPixelMatrix

    def make_transform(self, x, y) -> tuple:
        x_texture = x * self._t_m[0][0] + self._t_m[0][2]
        y_texture = y * self._t_m[1][1] + self._t_m[1][2]

        x_world = x_texture / self._texture_width
        y_world = 1.0 - y_texture / self._texture_height

        return x_world, y_world


class CellMetadata:
    MAX_BYTE_ID = 40

    def __init__(self, metadata_df: pandas.DataFrame, image_params: Optional[ImageParams] = None):
        self._volume_np: np.ndarray
        self._centroid_np: np.ndarray
        self._id_l: List[str]

        self._cells_count = 0
        self._load(metadata_df, image_params)

    def _load(self, metadata_df, image_params: Optional[ImageParams]):
        metadata_df = metadata_df.sort_index()
        self._id_l = [str(idl) for idl in metadata_df.index]
        self._cells_count = len(self._id_l)
        self._volume_np = metadata_df.loc[:, "volume"].values.tolist()
        centers_microns = metadata_df.loc[:, ["center_x", "center_y"]].values.tolist()

        if image_params is not None:
            point_transform = PointTransform(image_params)
            self._centroid_np = np.array(
                [point_transform.make_transform(coord[0], coord[1]) for coord in centers_microns]
            )

    def get_volume_array(self) -> np.ndarray:
        return self._volume_np

    def get_names_array(self) -> List[str]:
        return self._id_l

    def get_cell_metadata_array(self) -> bytearray:
        cell_metadata_btr = bytearray()
        for cell_idx in range(self._cells_count):
            extend_btr_by_fixed_str(cell_metadata_btr, self._id_l[cell_idx], self.MAX_BYTE_ID)
            extend_with_f32(cell_metadata_btr, self._volume_np[cell_idx])

            extend_with_f32(cell_metadata_btr, self._centroid_np[cell_idx][0])
            extend_with_f32(cell_metadata_btr, self._centroid_np[cell_idx][1])

        # write
        output_btr = bytearray()
        extend_with_u32(output_btr, self._cells_count)  # cell count
        extend_with_u32(output_btr, self.MAX_BYTE_ID)  # Size in bytes of one name

        output_btr.extend(cell_metadata_btr)
        return output_btr
