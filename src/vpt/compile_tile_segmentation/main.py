import json
import warnings
from typing import Callable, Tuple, Set, List, Optional, Dict

import numpy as np
import pandas as pd
from geopandas import GeoDataFrame
from pandas import Series

from vpt_core import log
from vpt_core.io.input_tools import read_parquet
from vpt_core.io.output_tools import save_segmentation_results
from vpt_core.io.vzgfs import filesystem_path_split, initialize_filesystem, io_with_retries
from vpt_core.segmentation.fuse import PolygonParams
from vpt_core.segmentation.seg_result import SegmentationResult

from vpt.compile_tile_segmentation.cmd_args import CompileTileSegmentationArgs, parse_cmd_args, validate_cmd_args
from vpt.compile_tile_segmentation.parameters import IOPaths, extract_parameters_from_spec, CompileParameters
from vpt.entity.relationships import create_entity_relationships, EntityRelationships
from vpt.run_segmentation_on_tile.output_utils import make_entity_output_filename
from vpt.utils.validate import validate_does_not_exist, validate_experimental

AdapterType = Callable[[int], SegmentationResult]


def combine_dataframes(
    get_tile_results: AdapterType,
    num_tiles: int,
) -> Tuple[SegmentationResult, Set]:
    seg_list = []

    log.info("Loading segmentation results")

    for tile_index in log.show_progress(range(num_tiles)):
        gdf = get_tile_results(tile_index)
        seg_list.append(gdf)
    log.info(f"Loaded results for {num_tiles} tiles")

    seg_compiled = SegmentationResult.combine_segmentations(seg_list)
    log.info("Concatenated dataframes")

    overlapped = SegmentationResult.find_overlapping_entities(seg_compiled.df)
    affected_entities = set(entity_id for pair in overlapped for entity_id in pair)
    return seg_compiled, affected_entities


def resolve_overlaps(
    seg_compiled: SegmentationResult,
    min_final_area: int,
    min_distance: int,
) -> SegmentationResult:
    seg_compiled.make_non_overlapping_polys(min_distance, min_final_area, log_progress=True)
    seg_compiled.set_column(SegmentationResult.detection_id_field, np.arange(len(seg_compiled.df), dtype=np.int64))

    log.info("Resolved overlapping in the compiled dataframe")
    return seg_compiled


def compile_dataframe(get_tile_results: AdapterType, params: CompileParameters) -> SegmentationResult:
    seg_compiled, _ = combine_dataframes(get_tile_results, params.num_tiles)

    min_final_area = list(params.polygon_parameters.values())[0].min_final_area
    min_distance = list(params.polygon_parameters.values())[0].min_distance_between_entities

    resolve_overlaps(
        seg_compiled=seg_compiled,
        min_final_area=min_final_area,
        min_distance=min_distance,
    )

    return seg_compiled


def adapter_from_paths(paths: IOPaths, entity_type: str) -> AdapterType:
    fs, _ = filesystem_path_split(paths.input_dir)

    def read(tile_index: int) -> SegmentationResult:
        path = fs.sep.join([paths.input_dir, make_entity_output_filename(tile_index, entity_type)])

        result = SegmentationResult(dataframe=read_parquet(path))

        return result

    return read


def update_affected_entities(compiled: List[SegmentationResult], affected_rows: List[Series]):
    def _get_new_affected_rows(df_to_update: GeoDataFrame, df_to_intersect: GeoDataFrame) -> Series:
        intersected_pairs = SegmentationResult.find_overlapping_entities(df_to_intersect, df_to_update)
        id_to_add = set(entity_id for entity_id, _ in intersected_pairs)

        # expand the set of affected entities with parent entities of affected children
        if any(df_to_intersect[SegmentationResult.parent_id_field].notnull()):
            id_to_add.union(df_to_intersect[SegmentationResult.parent_id_field])

        return df_to_update[SegmentationResult.cell_id_field].isin(id_to_add)

    affected_rows_old = [None for _ in affected_rows]
    # update the sets of affected rows for parent and child as long as at least one of them is still
    # changing and can affect the other set
    while any([any(old != affected) for old, affected in zip(affected_rows_old, affected_rows)]):
        affected_rows_old = [affected.copy() for affected in affected_rows]
        for i in range(len(compiled)):
            for j in range(i):
                new_rows_j = _get_new_affected_rows(compiled[j].df, compiled[i].df.loc[affected_rows[i]])
                new_rows_i = _get_new_affected_rows(compiled[i].df, compiled[j].df.loc[affected_rows[j]])

                affected_rows[j] = affected_rows[j] | new_rows_j
                affected_rows[i] = affected_rows[i] | new_rows_i

    return affected_rows


def create_relationships(
    compiled: List[SegmentationResult],
    affected_rows_set: List[Series],
    relationships: Optional[EntityRelationships],
    polygon_parameters: Dict[str, PolygonParams],
):
    # expand the set of affected entities with other types intersections
    affected_rows_set = update_affected_entities(compiled, affected_rows_set)
    to_update, partly_compiled = [], []
    for i in range(len(compiled)):
        update_part, other_part = split_segmentation_by_affected_part(compiled[i], affected_rows_set[i])
        to_update.append(update_part)
        partly_compiled.append(other_part)
    processed = create_entity_relationships(to_update, relationships, polygon_parameters)

    updated = []
    ids_update_info = dict()
    cell_field = SegmentationResult.cell_id_field

    def _shift_entity_ids(old_id: int, shift: int, min_id_to_update: int):
        return old_id + shift if not pd.isna(old_id) and old_id >= min_id_to_update else old_id

    # update the ids of newly created elements which might overlap with the set of ids of the partly compiled dataframe
    for partly_res in partly_compiled:
        updated_res = [seg_res for seg_res in processed if seg_res.entity_type == partly_res.entity_type][0]
        min_duplicated_id = updated_res.df[updated_res.df[cell_field].isin(partly_res.df[cell_field])][cell_field].min()
        if not pd.isna(min_duplicated_id):
            id_shift = partly_res.df[cell_field].max() - min_duplicated_id + 1
            updated_res.update_column(cell_field, _shift_entity_ids, shift=id_shift, min_id_to_update=min_duplicated_id)
            ids_update_info[updated_res.entity_type] = {"shift": id_shift, "min_id_to_update": min_duplicated_id}
        updated.append(updated_res)

    result = []
    for updated_res, partly_res in zip(updated, partly_compiled):
        # update links to parents whose identifiers have been shifted
        if len(updated_res.df) > 0:
            parent_type = updated_res.df[updated_res.parent_entity_field].unique()[0]
            if parent_type in ids_update_info.keys():
                updated_res.update_column(
                    updated_res.parent_id_field, _shift_entity_ids, **ids_update_info[parent_type]
                )
        result.append(SegmentationResult.combine_segmentations([updated_res, partly_res]))
        result[-1].set_entity_type(partly_res.entity_type)
    return result


def split_segmentation_by_affected_part(
    seg_res: SegmentationResult, affected_rows: Series
) -> Tuple[SegmentationResult, SegmentationResult]:
    result = SegmentationResult(dataframe=seg_res.df.loc[affected_rows])
    result.set_entity_type(seg_res.entity_type)

    part2 = SegmentationResult(dataframe=seg_res.df.drop(seg_res.df[affected_rows].index))
    part2.set_entity_type(seg_res.entity_type)
    return result, part2


def compile_tile_segmentation(args):
    # Suppress parquet / Arrow warnings
    warnings.filterwarnings("ignore", category=UserWarning)

    args = CompileTileSegmentationArgs(args.input_segmentation_parameters, args.max_row_group_size, args.overwrite)
    validate_cmd_args(args)
    log.info("Compile tile segmentation started")

    spec_raw = io_with_retries(args.parameters_json_path, "r", json.load)

    etype_to_paths, params = extract_parameters_from_spec(spec_raw)

    if len(etype_to_paths.keys()) > 1:
        validate_experimental()

    if not args.overwrite:
        for _, io_paths in etype_to_paths.items():
            validate_does_not_exist(io_paths.micron_output_file)
            validate_does_not_exist(io_paths.mosaic_output_file)

    compiled = []
    affected_rows_set = []
    deleted_entities = set()
    for entity_type, io_paths in etype_to_paths.items():
        result, affected_entities = combine_dataframes(adapter_from_paths(io_paths, entity_type), params.num_tiles)
        entities_ids = set(result.df[result.cell_id_field])
        result = resolve_overlaps(
            seg_compiled=result,
            min_final_area=params.polygon_parameters[entity_type].min_final_area,
            min_distance=params.polygon_parameters[entity_type].min_distance_between_entities,
        )
        deleted_entities |= entities_ids.difference(result.df[result.cell_id_field])
        affected_rows = result.df[result.cell_id_field].isin(affected_entities)
        result.set_entity_type(entity_type)
        compiled.append(result)
        affected_rows_set.append(affected_rows)

    # remove deleted parents from child dataframes
    parent_field = SegmentationResult.parent_id_field
    for i in range(len(compiled)):
        parent_removed = compiled[i].df[parent_field].isin(deleted_entities)
        affected_rows_set[i] = affected_rows_set[i] + parent_removed
        compiled[i].df.loc[parent_removed] = (
            compiled[i]
            .df.loc[parent_removed]
            .assign(**{parent_field: None, SegmentationResult.parent_entity_field: None}, dtype="object")
        )
    results = create_relationships(
        compiled, affected_rows_set, params.entity_type_relationships, params.polygon_parameters
    )
    for result in results:
        if not result.df[result.parent_id_field].isna().all():
            result.df[result.parent_id_field] = result.df[result.parent_id_field].astype("Int64")
        save_compiled_results(
            result, etype_to_paths[result.entity_type], params.micron_to_mosaic_matrix, args.max_row_group_size
        )

    log.info("Compile tile segmentation finished")


def save_compiled_results(result, output_paths, m2m_transform, max_row_group_size):
    save_segmentation_results(result.df, output_paths.micron_output_file, max_row_group_size)
    log.info(f"Saved compiled dataframe for entity {result.entity_type} in micron space")

    result.transform_geoms(m2m_transform)

    save_segmentation_results(result.df, output_paths.mosaic_output_file, max_row_group_size)
    log.info(f"Saved compiled dataframe for entity {result.entity_type} in mosaic space")


if __name__ == "__main__":
    initialize_filesystem()
    compile_tile_segmentation(parse_cmd_args())
