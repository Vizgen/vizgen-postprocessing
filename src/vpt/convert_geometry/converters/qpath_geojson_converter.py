from typing import Tuple, Dict

import geopandas as gpd
from shapely import geometry
from shapely.validation import make_valid

from vpt.convert_geometry.converters.entity_id_generator import set_process_id, get_id
from vpt.filesystem import vzg_open
from vpt.segmentation.utils.seg_result import SegmentationResult


def read_segmentation_result(input_path: str, entity_type: str, z_planes_number: int = 1,
                             spacing: float = 1.5) -> Tuple[SegmentationResult, Dict]:
    set_process_id()
    entity_ids_map = {}
    res = SegmentationResult()
    with vzg_open(str(input_path), 'r') as f:
        df = gpd.read_file(f)
        df.crs = None

        df.drop(columns=[col_name for col_name in df.columns if col_name != 'geometry'], inplace=True)
        df.rename(columns={'geometry': SegmentationResult.geometry_field}, inplace=True)

        entity_ids_map = {i: get_id() for i in range(len(df.index))}
        df = df.assign(**{SegmentationResult.cell_id_field: [entity_ids_map[i] for i in range(len(df))]})

        res = SegmentationResult(dataframe=df)
        res.update_geometry(lambda x:
                            make_valid(geometry.Polygon(x)) if isinstance(x, geometry.LineString)
                            else make_valid(x))

        res.set_entity_type(entity_type)
        res.set_column(SegmentationResult.entity_name_field, entity_type)
        res.set_column(SegmentationResult.detection_id_field, range(len(df)))
        res.set_column(SegmentationResult.z_index_field, 0)

        res.replicate_across_z(list(range(z_planes_number)))
        res.set_z_levels([spacing + (x * spacing) for x in range(z_planes_number)], 'ZLevel')

        set_none = ['Name', 'ParentID', 'ParentType']
        for column_name in set_none:
            res.set_column(column_name, None)
    return res, entity_ids_map
