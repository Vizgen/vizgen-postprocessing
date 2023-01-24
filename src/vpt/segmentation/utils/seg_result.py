from typing import List, Optional, Tuple, Set

import numpy as np
import pandas as pd
import shapely
from geopandas import GeoDataFrame, GeoSeries
from shapely import geometry, affinity
from shapely.ops import unary_union
from shapely.validation import make_valid

from vpt import log


class SegmentationResult:
    MAX_ENTITY_ID = 99999
    MAX_TILE_ID = 99999
    MAX_TASK_ID = 9
    detection_id_field: str = 'ID'
    cell_id_field: str = 'EntityID'
    z_index_field: str = 'ZIndex'
    geometry_field: str = 'Geometry'
    entity_name_field: str = 'Type'
    entity_type: str
    df: GeoDataFrame

    def __init__(self, list_data=None, dataframe: Optional[GeoDataFrame] = None, entity: Optional[str] = None):
        if list_data is None and dataframe is None:
            list_data = []
        if dataframe is not None:
            self.df = dataframe.copy()
        else:
            self.df = GeoDataFrame(list_data, columns=[self.detection_id_field, self.cell_id_field, self.z_index_field,
                                                       self.geometry_field])
        if entity is not None:
            self.entity_type = entity
        self.df.set_geometry(self.geometry_field, inplace=True)
        self.df.loc[:, self.cell_id_field] = self.df.loc[:, self.cell_id_field].astype('int64')

    def update_column(self, column_name: str, callback: callable, *args, **kwargs):
        self.df[column_name] = self.df[column_name].apply(lambda x: callback(x, *args, **kwargs))

    def update_geometry(self, callback: callable, *args, **kwargs):
        from vpt.segmentation.utils.polygon_utils import convert_to_multipoly

        def transform(x) -> geometry.MultiPolygon:
            return convert_to_multipoly(callback(x, *args, **kwargs))

        self.df[self.geometry_field] = self.df[self.geometry_field].apply(transform)

    def set_column(self, column_name: str, data):
        kwargs = {column_name: data}
        self.df = self.df.assign(**kwargs)

    def remove_column(self, column_name):
        if column_name in self.df.columns:
            self.df.drop(columns=[column_name], inplace=True)

    def set_entity_type(self, entity: str):
        self.entity_type = entity

    def translate_geoms(self, dx, dy):
        self.update_geometry(affinity.translate, xoff=dx, yoff=dy)

    def transform_geoms(self, matrix):
        tform_flat = [*matrix[:2, :2].flatten(), *matrix[:2, 2].flatten()]
        self.update_geometry(affinity.affine_transform, matrix=tform_flat)

    def remove_polys(self, condition, *args, **kwargs):
        indices_to_remove = []
        for idx, row in self.df.iterrows():
            if condition(row[self.geometry_field], *args, **kwargs):
                indices_to_remove.append(idx)
        if len(indices_to_remove) > 0:
            self.df.drop(indices_to_remove, inplace=True)

    def _get_replication_pairs(self, z_planes: Set[int]):
        copy_pairs = []
        if len(self.df) < 1:
            return copy_pairs
        occupied = set(self.df['ZIndex'].to_list())
        exceptional_z = min(z_planes) - 1
        while z_planes != occupied:
            missing_layers = z_planes.difference(occupied)
            neighbor_layers = [[present if abs(present - missing) == 1 else exceptional_z for present in occupied] for
                               missing in missing_layers]
            layer_pairs = [(missing, max(neighbor)) for missing, neighbor in zip(missing_layers, neighbor_layers) if
                           any([z != exceptional_z for z in neighbor])]
            if len(layer_pairs) == 0:
                return copy_pairs

            copy_pairs.extend(layer_pairs)
            for x in layer_pairs:
                occupied.add(x[0])
        return copy_pairs

    def replicate_across_z(self, z_planes: List[int]):
        replicate_pairs = self._get_replication_pairs(set(z_planes))
        for missing_z, copy_z in replicate_pairs:
            missing_z_seg = SegmentationResult(dataframe=self.df.loc[self.df[self.z_index_field] == copy_z])
            missing_z_seg.set_column(self.z_index_field, missing_z)
            self.df = self.combine_segmentations([self, missing_z_seg]).df

    def set_z_levels(self, z_levels: List[float], column_name):
        levels = [z_levels[row[self.z_index_field]] for _, row in self.df.iterrows()]
        self.set_column(column_name, levels)

    def fuse_across_z(self, parameters):
        z_lines = self.df['ZIndex'].unique()
        reserved_ids = []
        for z_i in range(1, z_lines.shape[0]):
            prev_df = self.df.loc[self.df[self.z_index_field] == z_lines[z_i - 1]]
            cur_df = self.df.loc[self.df[self.z_index_field] == z_lines[z_i]]
            geom_0 = prev_df[self.geometry_field].to_list()
            geom_1 = cur_df[self.geometry_field].to_list()
            reserved_ids += prev_df[self.cell_id_field].to_list()
            cur_cells_ids = np.unique(cur_df[self.cell_id_field].to_list())

            tree = shapely.STRtree(geom_0)
            pairs = tree.query(geom_1, predicate="intersects")
            cur_ids_intersected = [cur_df[self.cell_id_field].iloc[x] for x in pairs[0]]
            prev_ids_intersected = [prev_df[self.cell_id_field].iloc[x] for x in pairs[1]]
            for i in range(len(cur_cells_ids)):
                cur_i = cur_cells_ids[i]
                cur_intersected_i_to_update = []
                need_new_index = True
                if cur_i in cur_ids_intersected:
                    for pair_i in [idx for idx, x in enumerate(cur_ids_intersected) if x == cur_i]:
                        prev_i = prev_ids_intersected[pair_i]
                        prev_poly = prev_df[prev_df[self.cell_id_field] == prev_i][self.geometry_field].to_list()[0]
                        cur_poly = cur_df[cur_df[self.cell_id_field] == cur_i][self.geometry_field].to_list()[0]
                        polys_intersection = prev_poly.intersection(cur_poly)
                        polys_union = unary_union([prev_poly, cur_poly])
                        if polys_intersection.area / polys_union.area >= 0.5:
                            need_new_index = False
                            if prev_i != cur_i:
                                if prev_i in cur_cells_ids:
                                    new_id = max(max(reserved_ids), max(cur_cells_ids)) + 1
                                    cur_intersected_i_to_update.append((prev_i, new_id))
                                cur_intersected_i_to_update.append((cur_i, prev_i))
                            break
                if need_new_index:
                    if cur_i in reserved_ids:
                        new_id = max(max(reserved_ids), max(cur_cells_ids)) + 1
                        cur_intersected_i_to_update.append((cur_i, new_id))
                for old_id, new_id in cur_intersected_i_to_update:
                    for j in cur_df.loc[cur_df[self.cell_id_field] == old_id].index:
                        self.df.at[j, self.cell_id_field] = new_id
                    cur_df = self.df.loc[self.df[self.z_index_field] == z_lines[z_i]]
                    update_ids = np.where(cur_cells_ids == old_id)
                    for idx in update_ids:
                        cur_cells_ids[idx] = new_id
                    if old_id in cur_ids_intersected:
                        cur_ids_intersected = [cell_id if cell_id != old_id else new_id
                                               for cell_id in cur_ids_intersected]

    def remove_edge_polys(self, tile_size: Tuple[int, int]):
        crop_frame = geometry.box(-10, -10, tile_size[0] + 10, tile_size[1] + 10) - \
                     geometry.box(5, 5, tile_size[0] - 5, tile_size[1] - 5)
        for entity_id in self.df[self.cell_id_field].unique():
            cur_gdf = self.df.loc[self.df[self.cell_id_field] == entity_id]
            is_intersected = False
            for z in cur_gdf[self.z_index_field]:
                cur_geom_df = cur_gdf.loc[cur_gdf[self.z_index_field] == z, self.geometry_field]
                if len(cur_geom_df) == 0:
                    continue
                if any(cur_geom_df.values.intersects(crop_frame)):
                    is_intersected = True
                    break
            if is_intersected:
                self.df = self.df.drop(self.df.loc[self.df[self.cell_id_field] == entity_id].index.to_list())

    def _resolve_cell_overlap(self, large_cell: GeoDataFrame, small_cell: GeoDataFrame, min_distance: int):
        """
        Trims area from larger entity
        """
        from vpt.segmentation.utils.polygon_utils import convert_to_multipoly

        z_planes_in_both = set(large_cell[self.z_index_field]).intersection(set(small_cell[self.z_index_field]))

        for z in z_planes_in_both:
            # Gets the large and small geometries
            large_at_z_idx = large_cell.loc[large_cell[self.z_index_field] == z].index[0]
            small_at_z_idx = small_cell.loc[small_cell[self.z_index_field] == z].index[0]

            large_at_z = self.df.at[large_at_z_idx, self.geometry_field]
            small_at_z = self.df.at[small_at_z_idx, self.geometry_field]

            # Trims the larger geometry with a small buffer
            valid_large = make_valid(large_at_z)
            valid_small = make_valid(small_at_z)

            trimmed_raw = valid_large.difference(valid_small.buffer(min_distance))
            trimmed_geometry = convert_to_multipoly(make_valid(trimmed_raw))

            # Overwrites large geometry with trimmed geometry
            self.df.at[large_at_z_idx, self.geometry_field] = trimmed_geometry

    def _find_overlapping_entities(self):
        """
        Uses shapely library to rapidly identify entities that overlap in 3D
        """

        entity_overlap = []
        for _, gdf in self.df.groupby(self.z_index_field):
            geom_list = gdf[self.geometry_field].tolist()

            # Find overlapping cells in this z-plane
            tree = shapely.STRtree(geom_list)
            overlap = tree.query(geom_list, predicate="intersects")

            # Remove self-intersections
            overlap = np.array([pair for pair in overlap.T if pair[0] != pair[1]])

            # Map list positions back to Entity IDs and add to overall overlap list
            for geom_pair in overlap:
                left = gdf[self.cell_id_field].iloc[geom_pair[0]]
                right = gdf[self.cell_id_field].iloc[geom_pair[1]]
                entity_overlap.append((left, right))

        # Remove repeated sets of EntityIDs
        return list(set(frozenset(pair) for pair in entity_overlap))

    def get_volume(self):
        return np.sum([x.area for x in self.df[self.geometry_field]])

    def get_z_planes(self) -> Set:
        return set(self.df[self.z_index_field])

    def get_z_geoms(self, z_line: int) -> GeoSeries:
        return self.df.loc[self.df[self.z_index_field] == z_line, self.geometry_field]

    @staticmethod
    def _get_overlapping_volume(left_seg_result, right_seg_result):
        """
        Calulates intersection area for 3D shapes stored in a geo data frame.
        """
        left_entity = dict(
            zip(
                left_seg_result.df[SegmentationResult.z_index_field],
                left_seg_result.df[SegmentationResult.geometry_field]
            )
        )
        right_entity = dict(
            zip(
                right_seg_result.df[SegmentationResult.z_index_field],
                right_seg_result.df[SegmentationResult.geometry_field]
            )
        )
        intersection_area = 0
        for z in left_entity:
            if z in right_entity:
                intersection_area += make_valid(left_entity[z]).intersection(make_valid(right_entity[z])).area
        return intersection_area

    @staticmethod
    def combine_segmentations(segmentations: List):
        to_concat = [seg.df for seg in segmentations if len(seg.df) > 0]
        if len(to_concat) > 1:
            df = GeoDataFrame(pd.concat(to_concat, ignore_index=True))
            duplicated_fields = [SegmentationResult.cell_id_field, SegmentationResult.z_index_field]
            deprecated_indexes = df[df.duplicated(duplicated_fields)].index
            if len(deprecated_indexes) > 0:
                log.warning(f'Found several entity rows for the same z planes. {len(deprecated_indexes)} rows will be '
                            f'removed from segmentation result.')
                df.drop(deprecated_indexes, inplace=True)
            res = SegmentationResult(dataframe=df)
            res.set_column(SegmentationResult.detection_id_field, list(range(len(res.df))))
            return res
        else:
            return segmentations[0] if len(segmentations) > 0 else SegmentationResult()

    def _union_entities(self, base_gdf, add_gdf):
        """
        Adds the area from entity_id_add to entity_id_base across z-levels
        """
        from vpt.segmentation.utils.polygon_utils import convert_to_multipoly

        # Area of intersection
        add_entity = dict(zip(add_gdf[self.z_index_field], add_gdf[self.geometry_field]))

        occupied_z_planes = set(base_gdf[self.z_index_field]).intersection(set(add_entity))
        for z in occupied_z_planes:

            base_geoms = base_gdf.loc[base_gdf[self.z_index_field] == z]
            if len(base_geoms) == 0:
                continue
            if z not in add_entity:
                continue
            base_geom_z_idx = base_geoms.index[0]

            base_geom = base_gdf.at[base_geom_z_idx, self.geometry_field]
            add_geom = add_entity[z]

            valid_base = make_valid(base_geom)
            valid_add = make_valid(add_geom)

            union_raw = valid_base.union(valid_add)
            union_geom = convert_to_multipoly(make_valid(union_raw))

            # Overwrites large geometry with trimmed geometry
            self.df.at[base_geom_z_idx, self.geometry_field] = union_geom

    def cell_size_filter(self, minimum_area: int):
        depricated_entity_ids = []
        for entity_id, gdf in self.df.groupby(self.cell_id_field):
            if len(gdf) > 0 and not any(cell.area > minimum_area for cell in gdf[self.geometry_field]):
                depricated_entity_ids.append(entity_id)
        self._drop_by_entity_id(depricated_entity_ids)

    def make_non_overlapping_polys(self, min_distance: int = 2, min_area: int = 100, log_progress: bool = False):
        # Find cells that have any overlapping area
        problem_sets = self._find_overlapping_entities()
        log.info(f'Found {len(problem_sets)} overlaps')

        # For each pair of overlapping cells, resolve the conflict
        depricated_entity_ids = []
        iterate = log.show_progress if log_progress else lambda x: x

        # Union the large overlap Entities
        for problem in iterate(problem_sets):
            # Get the slice of the dataframe for each entity
            pl = list(problem)
            entity_id_left, entity_id_right = pl[0], pl[1]

            # If either cell is in the depricated id list, ignore the overlap.
            # The entity union / drop process may drop a cell that should be retained.
            if entity_id_left in depricated_entity_ids or entity_id_right in depricated_entity_ids:
                continue

            left = SegmentationResult(dataframe=self.df.loc[self.df[self.cell_id_field] == entity_id_left])
            right = SegmentationResult(dataframe=self.df.loc[self.df[self.cell_id_field] == entity_id_right])

            # Find seperate and overlapping volumes of the cells
            volume_left = left.get_volume()
            volume_right = right.get_volume()
            overlap_volume = SegmentationResult._get_overlapping_volume(left, right)
            overlap_volume_percent = overlap_volume / min(volume_right, volume_left)

            # If overlap is > 50% of either cell, eliminate the small cell and keep the big one
            if overlap_volume_percent > 0.5:
                if volume_left > volume_right:
                    self._union_entities(left.df, right.df)
                    depricated_entity_ids.append(entity_id_right)
                else:
                    self._union_entities(right.df, left.df)
                    depricated_entity_ids.append(entity_id_left)

        # With large overlaps resolved, re-identify problem sets and trim overlaps
        self._drop_by_entity_id(depricated_entity_ids)
        problem_sets = self._find_overlapping_entities()
        log.info(f'After union of large overlaps, found {len(problem_sets)} overlaps')

        for problem in iterate(problem_sets):
            # Get the slice of the dataframe for each entity
            pl = list(problem)
            entity_id_left, entity_id_right = pl[0], pl[1]
            left = SegmentationResult(dataframe=self.df.loc[self.df[self.cell_id_field] == entity_id_left])
            right = SegmentationResult(dataframe=self.df.loc[self.df[self.cell_id_field] == entity_id_right])

            # Find seperate and overlapping volumes of the cells
            volume_left = left.get_volume()
            volume_right = right.get_volume()

            # Trim the larger cell to dodge the smaller cell
            if volume_left > volume_right:
                self._resolve_cell_overlap(left.df, right.df, min_distance)
            else:
                self._resolve_cell_overlap(right.df, left.df, min_distance)

        # After both steps, check for any remaining overlaps
        problem_sets = self._find_overlapping_entities()
        log.info(f'After both resolution steps, found {len(problem_sets)} uncaught overlaps')

        # Filter any small cells that were created
        self.cell_size_filter(min_area)

    def union_intersections(self, min_distance: int, min_area: int):
        problem_sets = self._find_overlapping_entities()
        depricated_entity_ids = []
        for problem in problem_sets:
            entity_id_left, entity_id_right, *_ = list(problem)
            left_df = self.df.loc[self.df[self.cell_id_field] == entity_id_left]
            right_df = self.df.loc[self.df[self.cell_id_field] == entity_id_right]
            self._union_entities(left_df, right_df)
            depricated_entity_ids.append(entity_id_right)
        self._drop_by_entity_id(depricated_entity_ids)
        self.cell_size_filter(min_area)

    def larger_resolve_intersections(self, min_distance: int, min_area: int):
        problem_sets = self._find_overlapping_entities()
        depricated_entity_ids = []
        for problem in problem_sets:
            entity_id_left, entity_id_right, *_ = list(problem)
            left = SegmentationResult(dataframe=self.df.loc[self.df[self.cell_id_field] == entity_id_left])
            right = SegmentationResult(dataframe=self.df.loc[self.df[self.cell_id_field] == entity_id_right])
            left_area, right_area = left.get_volume(), right.get_volume()
            if left_area > right_area:
                depricated_entity_ids.append(entity_id_right)
            else:
                depricated_entity_ids.append(entity_id_left)
        self._drop_by_entity_id(depricated_entity_ids)
        self.cell_size_filter(min_area)

    def _drop_by_entity_id(self, entity_ids_to_delete):
        depricated_row_indexes = []
        for entity_id in entity_ids_to_delete:
            row_indexes = self.df.loc[self.df[self.cell_id_field] == entity_id].index.to_list()
            depricated_row_indexes.extend(row_indexes)
        self.df.drop(depricated_row_indexes, inplace=True)
