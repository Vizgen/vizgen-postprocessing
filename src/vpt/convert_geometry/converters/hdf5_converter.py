from typing import Dict, Tuple

import h5py
import numpy as np
from h5py import Group
from shapely import geometry
from shapely.validation import make_valid
from vpt_core.io.vzgfs import vzg_open, retrying_attempts
from vpt_core.segmentation.polygon_utils import convert_to_multipoly
from vpt_core.segmentation.seg_result import SegmentationResult

from vpt.convert_geometry.converters.entity_id_generator import get_id, set_process_id


def read_segmentation_result(input_path: str, entity_type: str) -> Tuple[SegmentationResult, Dict]:
    set_process_id()
    entity_ids_map = {}
    segmentations = []
    try:
        for attempt in retrying_attempts():
            with attempt, vzg_open(input_path, "rb") as f:
                h = h5py.File(f, "r")
                group = h.require_group("featuredata")
                for k in group.keys():
                    entity_id = get_id()
                    segmentations.append(load_feature_from_hdf5_group(group[k], entity_id))
                    entity_ids_map[group[k].attrs["id"]] = entity_id
    except Exception as err:
        raise ValueError(
            f"Hdf5 file structure is wrong and is not compatible with " f"merlin output hdf5 segmentation. {err}"
        )
    res = SegmentationResult.combine_segmentations(segmentations)
    res.set_entity_type(entity_type)
    res.set_column(SegmentationResult.entity_name_field, res.entity_type)

    set_none = ["Name", "ParentID", "ParentType"]
    for column_name in set_none:
        res.set_column(column_name, None)
    return res, entity_ids_map


def load_geometry_from_hdf5_group(h5Group: Group):
    geometry_params = {"type": h5Group.attrs["type"].decode(), "coordinates": np.array(h5Group["coordinates"])}
    return convert_to_multipoly(make_valid(geometry.shape(geometry_params)))


def load_feature_from_hdf5_group(h5Group: Group, cell_id: np.int64):
    zCount = len([x for x in h5Group.keys() if x.startswith("zIndex_")])
    polys_data = []
    idx = 0
    for z in range(zCount):
        zGroup = h5Group["zIndex_" + str(z)]
        pCount = len([x for x in zGroup.keys() if x[:2] == "p_"])
        if pCount == 0:
            continue
        multipolys = [load_geometry_from_hdf5_group(zGroup["p_" + str(p)]) for p in range(pCount)]
        multipoly: geometry.MultiPolygon = multipolys[0]
        for poly in multipolys[1:]:
            multipoly = convert_to_multipoly(make_valid(multipoly.union(poly)))

        polys_data.append(
            {
                SegmentationResult.detection_id_field: idx,
                SegmentationResult.cell_id_field: cell_id,
                SegmentationResult.z_index_field: z,
                SegmentationResult.geometry_field: multipoly,
                "ZLevel": h5Group["z_coordinates"][z],
            }
        )
        idx += 1
    seg_res = SegmentationResult(list_data=polys_data)
    seg_res.set_column("ZLevel", seg_res.df[SegmentationResult.z_index_field])
    seg_res.update_column("ZLevel", lambda x: h5Group["z_coordinates"][x])
    return seg_res
