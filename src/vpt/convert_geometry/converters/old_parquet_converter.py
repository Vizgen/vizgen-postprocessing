from typing import Tuple, Dict

import geopandas as gpd

from vpt.convert_geometry.converters.entity_id_generator import set_process_id, get_id
from vpt.filesystem import vzg_open
from vpt.segmentation.utils.seg_result import SegmentationResult


def read_segmentation_result(input_path: str, entity_type: str, z_planes_number: int = 0,
                             spacing: float = 1.5) -> Tuple[SegmentationResult, Dict]:
    set_process_id()
    with vzg_open(input_path, 'rb') as f:
        pq = gpd.read_parquet(f)

    if SegmentationResult.cell_id_field not in pq.columns:
        pq = pq.assign(**{SegmentationResult.cell_id_field: list(range(len(pq)))})
    entity_ids_map = {i: get_id() for i in pq[SegmentationResult.cell_id_field].unique()}

    seg_res = SegmentationResult(dataframe=pq)
    seg_res.update_column(SegmentationResult.cell_id_field, entity_ids_map.get)

    seg_res.set_entity_type(entity_type)
    if seg_res.entity_name_field not in seg_res.df.columns:
        seg_res.set_column(SegmentationResult.entity_name_field, entity_type)

    if seg_res.detection_id_field not in seg_res.df.columns:
        seg_res.set_column(SegmentationResult.detection_id_field, list(range(len(pq))))

    if seg_res.z_index_field not in seg_res.df.columns:
        seg_res.set_column(SegmentationResult.z_index_field, 0)

    if z_planes_number > 0:
        if len(seg_res.df[seg_res.z_index_field].unique()) > 1:
            raise ValueError('The input segmentation is already 3D. The conversion to 3D only possible for 2D '
                             'segmentation')

        z_planes = list(range(z_planes_number))
        if not set(z_planes).issuperset(seg_res.df[seg_res.z_index_field].unique()):
            raise ValueError('The z plane set of the input segmentation should be a subset of the requested set of '
                             'output z planes')

        seg_res.replicate_across_z(z_planes)
        seg_res.set_z_levels([spacing + (x * spacing) for x in z_planes], 'ZLevel')

    set_none = ['Name', 'ParentID', 'ParentType']
    for column_name in set_none:
        if column_name not in seg_res.df:
            seg_res.set_column(column_name, None)
    return seg_res, entity_ids_map
