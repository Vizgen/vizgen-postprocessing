import argparse
import os
from typing import Optional, Sequence

import pandas as pd
import shutil

from vpt.filesystem import vzg_open, initialize_filesystem
from vpt.app.task import Task
from vpt.app.context import parallel_run, current_context
from vpt.update_vzg.polygons.packedpolygon import LodLevel
from vpt.utils.boundaries import Boundaries
from vpt.derive_cell_metadata.cell_metadata import create_metadata_table
from vpt.update_vzg.assemble.dataset_assemble import run_dataset_assembling
from vpt.update_vzg.cmd_args import get_parser, validate_args
from vpt.update_vzg.cell_metadata import CellMetadata
from vpt.update_vzg.imageparams import load_image_parameters
from vpt.update_vzg.polygon_transfer import CellTransfer, CellsTransfer
from vpt.utils.cellsreader import cell_reader_factory, CellsReader
from vpt.utils.general_data import write_file
from vpt.utils.vzgrepacker import VzgRepacker
import vpt.log as log


def _process(args):
    cells_reader: CellsReader = cell_reader_factory(args.input_boundaries)
    fov_count = cells_reader.get_fovs_count()
    z_count = cells_reader.get_z_planes_count()
    image_params = load_image_parameters(args.data_folder)
    cell_transfer = CellTransfer(image_params)
    results_list = []
    for fov_idx in range(args.task_index, fov_count, args.processes):
        raw_cells = cells_reader.read_fov(fov_idx)
        results = cell_transfer.process_cells(raw_cells, fov_idx)
        results_list.extend(results)
    return results_list, z_count


def main_update_vzg(args):
    validate_args(args)

    vzg_repacker = VzgRepacker(args.input_vzg, args.temp_path)
    vzg_repacker.unpack_vzg()
    dataset_folder = vzg_repacker.get_dataset_folder()
    gene_array = vzg_repacker.read_genes_info_array()

    cells_folder = os.path.join(dataset_folder, 'cells_packed')
    if os.path.exists(cells_folder):
        shutil.rmtree(os.path.join(cells_folder))

    if not args.input_metadata:
        log.info('There is no cell metadata on input, start creating')
        initialize_filesystem()
        args.input_metadata = os.path.join(args.temp_path, 'cell_metadata.csv')
        cells_reader: CellsReader = cell_reader_factory(args.input_boundaries)
        cell_bounds = Boundaries(cells_reader)
        metadata_table = create_metadata_table(cell_bounds, cells_reader.get_z_levels())

        with vzg_open(args.input_metadata, 'w') as f:
            metadata_table.to_csv(f, sep=',')
        log.info('Cell metadata file created')

    image_params = load_image_parameters(dataset_folder)
    with vzg_open(args.input_metadata, 'r') as f:
        cell_metadata: pd.DataFrame = pd.read_csv(f, index_col=0)

    # Sort the metadata table by EntityID if it isn't already sorted
    cell_metadata = cell_metadata.sort_index()

    vzg_metadata = CellMetadata(cell_metadata, image_params)
    vzg_metadata_bin_array = vzg_metadata.get_cell_metadata_array()
    write_file(dataset_folder, vzg_metadata_bin_array, 'cell_metadata_array.bin', 'cells_packed')

    polygon_list = []
    num_processes = current_context().get_workers_count()
    log.info(f'Running cell assembly in {num_processes} processes')
    results = parallel_run(
        [Task(_process, argparse.Namespace(
            input_boundaries=args.input_boundaries,
            data_folder=dataset_folder,
            task_index=i,
            processes=num_processes)) for i in range(num_processes)])

    z_count = vzg_repacker.read_dataset_z_planes_count()
    z_count_cells = 1
    for result, number_z_planes in results:
        polygon_list.extend(result)
        z_count_cells = max(z_count_cells, number_z_planes)

    if z_count_cells > z_count:
        raise IndexError(f'Z planes count in parquet files {z_count_cells} more then in vzg {z_count}')

    cell_transfer = CellsTransfer(vzg_metadata, z_count, image_params)
    cell_transfer.fill_grid(polygon_list)

    lod_level_path = {
        LodLevel.Max: 'max',
        LodLevel.Middle: 'middle',
        LodLevel.Min: 'min'
    }

    for lod_level in [LodLevel.Max, LodLevel.Middle, LodLevel.Min]:

        file_path = os.path.join('cells_packed', lod_level_path[lod_level])
        cells_byte_arrays = cell_transfer.get_cells_by_lod(lod_level)
        for z_slice, cells_byte_array in enumerate(cells_byte_arrays):
            write_file(dataset_folder, cells_byte_array, 'cell_{0}.bin'.format(z_slice), file_path)

        poly_binary_array, cell_binary_array = cell_transfer.get_poly_pointer_arrays()
        write_file(dataset_folder, poly_binary_array, 'poly_pointer_array.bin', file_path)
        write_file(dataset_folder, cell_binary_array, 'cell_array.bin', file_path)

    log.info('Cells binaries generation completed')

    all_genes = list(record['name'] for record in gene_array['transcriptsPerGeneList'])

    run_dataset_assembling(args.input_entity_by_gene, dataset_folder, vzg_metadata, genes=all_genes)
    log.info('Assembler data binaries generation complected')

    vzg_repacker.repack_vzg_file(os.path.splitext(args.output_vzg)[0], image_params)
    log.info('Update VZG completed')


def parse_args(args: Optional[Sequence[str]] = None) -> argparse.Namespace:
    return get_parser().parse_args(args)
