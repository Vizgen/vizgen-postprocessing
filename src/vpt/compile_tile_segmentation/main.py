import json
import warnings
from typing import Callable

import geopandas as gpd
import numpy as np

import vpt.log as log
from vpt.compile_tile_segmentation.cmd_args import parse_cmd_args, CompileTileSegmentationArgs, validate_cmd_args
from vpt.compile_tile_segmentation.parameters import CompileParameters, IOPaths, extract_parameters_from_spec
from vpt.filesystem.vzgfs import filesystem_path_split, initialize_filesystem, vzg_open
from vpt.run_segmentation_on_tile.output_utils import make_output_filename
from vpt.segmentation.utils.seg_result import SegmentationResult
from vpt.utils.output_tools import save_segmentation_results
from vpt.utils.validate import validate_does_not_exist

AdapterType = Callable[[int], SegmentationResult]


def compile_dataframe(get_tile_results: AdapterType, params: CompileParameters) -> SegmentationResult:
    seg_list = []

    log.info('Loading segmentation results')

    for tile_index in log.show_progress(range(params.num_tiles)):
        gdf = get_tile_results(tile_index)
        seg_list.append(gdf)
    log.info(f'Loaded results for {params.num_tiles} tiles')

    seg_compiled = SegmentationResult.combine_segmentations(seg_list)
    log.info('Concatenated dataframes')

    mosaic_to_micron = np.linalg.inv(params.micron_to_mosaic_matrix)
    x_scale, y_scale = mosaic_to_micron[0, 0], mosaic_to_micron[1, 1]

    min_final_area = params.min_final_area * x_scale * y_scale
    min_distance = params.min_distance * x_scale

    seg_compiled.make_non_overlapping_polys(min_distance, min_final_area, log_progress=True)
    seg_compiled.set_column(SegmentationResult.detection_id_field, np.arange(len(seg_compiled.df), dtype=np.int64))

    log.info('Resolved overlapping in the compiled dataframe')
    return seg_compiled


def adapter_from_paths(paths: IOPaths) -> AdapterType:
    fs, input_dir = filesystem_path_split(paths.input_dir)

    def read(tile_index: int) -> SegmentationResult:
        path = fs.sep.join([input_dir, make_output_filename(tile_index)])

        result = None

        with fs.open(path, 'rb') as f:
            result = SegmentationResult(dataframe=gpd.read_parquet(f))

        return result

    return read


def compile_tile_segmentation(args):
    # Suppress parquet / Arrow warnings
    warnings.filterwarnings('ignore', category=UserWarning)

    args = CompileTileSegmentationArgs(args.input_segmentation_parameters, args.max_row_group_size, args.overwrite)
    validate_cmd_args(args)
    log.info('Compile tile segmentation started')

    with vzg_open(args.parameters_json_path, 'r') as f:
        spec_raw = json.load(f)

    etype_to_paths, params = extract_parameters_from_spec(spec_raw)

    if not args.overwrite:
        for _, io_paths in etype_to_paths.items():
            validate_does_not_exist(io_paths.micron_output_file)
            validate_does_not_exist(io_paths.mosaic_output_file)

    for entity_type, io_paths in etype_to_paths.items():
        compiled = compile_dataframe(adapter_from_paths(io_paths), params)

        save_segmentation_results(compiled.df, io_paths.micron_output_file, args.max_row_group_size)
        log.info('Saved compiled dataframe in micron space')

        compiled.transform_geoms(params.micron_to_mosaic_matrix)

        save_segmentation_results(compiled.df, io_paths.mosaic_output_file, args.max_row_group_size)
        log.info('Saved compiled dataframe in mosaic space')

    log.info('Compile tile segmentation finished')


if __name__ == '__main__':
    initialize_filesystem()
    compile_tile_segmentation(parse_cmd_args())
