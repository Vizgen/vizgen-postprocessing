import argparse
import os
import shutil
from typing import Optional, Sequence, List, Tuple

import pandas as pd

from vpt.utils.input_utils import read_segmentation_entity_types
from vpt_core import log
from vpt_core.io.vzgfs import io_with_retries

from vpt.app.context import current_context, parallel_run
from vpt.app.task import Task
from vpt.derive_cell_metadata.cell_metadata import create_input_metadata
from vpt.update_vzg.assemble.dataset_assemble import identify_sequential, run_dataset_assembling
from vpt.update_vzg.cell_metadata import CellMetadata
from vpt.update_vzg.cmd_args import get_parser, validate_args, initialize_experimental_args
from vpt.update_vzg.imageparams import load_image_parameters, ImageParams
from vpt.update_vzg.polygon_transfer import CellsTransfer, CellTransfer
from vpt.update_vzg.polygons.packedpolygon import LodLevel
from vpt.update_vzg.polygons.polygonset import PolygonSet
from vpt.utils.cellsreader import CellsReader, cell_reader_factory
from vpt.utils.general_data import write_file
from vpt.utils.vzgrepacker import VzgRepacker


def _process(args) -> Tuple[List[PolygonSet], int]:
    cells_reader: CellsReader = cell_reader_factory(args.input_boundaries)
    fov_count = cells_reader.get_fovs_count()
    z_count = cells_reader.get_z_planes_count()
    image_params = load_image_parameters(args.data_folder)
    cell_transfer = CellTransfer(image_params)
    results_list = []
    log.info("running cells processing for fovs")
    log.log_system_info()
    for fov_idx in range(args.task_index, fov_count, args.processes):
        raw_cells = cells_reader.read_fov(fov_idx)
        results = cell_transfer.process_cells(raw_cells, fov_idx)
        results_list.extend(results)
    return results_list, z_count


def update_feature(
    vzg_repacker: VzgRepacker,
    input_metadata: str,
    input_boundaries: str,
    input_entity_by_gene: str,
    image_params: ImageParams,
    feature_name: str,
):
    dataset_folder = vzg_repacker.get_dataset_folder()
    channels = vzg_repacker.get_manifest_channels()
    feature_folder = vzg_repacker.get_feature_folder(feature_name)

    cell_metadata: pd.DataFrame = io_with_retries(input_metadata, "r", lambda f: pd.read_csv(f, index_col=0))

    # Sort the metadata table by EntityID if it isn't already sorted
    cell_metadata = cell_metadata.sort_index()

    vzg_metadata = CellMetadata(cell_metadata, image_params)
    vzg_metadata_bin_array = vzg_metadata.get_cell_metadata_array()
    write_file(feature_folder, vzg_metadata_bin_array, "cell_metadata_array.bin", "cells_packed")

    polygon_list: List[PolygonSet] = []
    num_processes = current_context().get_workers_count()
    log.info(f"Running cell assembly in {num_processes} processes for feature {feature_name}")
    results = parallel_run(
        [
            Task(
                _process,
                argparse.Namespace(
                    input_boundaries=input_boundaries,
                    data_folder=dataset_folder,
                    task_index=i,
                    processes=num_processes,
                ),
            )
            for i in range(num_processes)
        ]
    )
    z_count = vzg_repacker.read_dataset_z_planes_count()
    z_count_cells = 1
    for result, number_z_planes in results:
        polygon_list.extend(result)
        z_count_cells = max(z_count_cells, number_z_planes)

    if z_count_cells > z_count:
        raise IndexError(f"Z planes count in parquet files {z_count_cells} more then in vzg {z_count}")

    cell_transfer = CellsTransfer(vzg_metadata, z_count, image_params)
    cell_transfer.fill_grid(polygon_list)

    lod_level_path = {LodLevel.Max: "max", LodLevel.Middle: "middle", LodLevel.Min: "min"}

    for lod_level in [LodLevel.Max, LodLevel.Middle, LodLevel.Min]:
        file_path = os.path.join("cells_packed", lod_level_path[lod_level])
        cells_byte_arrays = cell_transfer.get_cells_by_lod(lod_level)
        for z_slice, cells_byte_array in enumerate(cells_byte_arrays):
            write_file(feature_folder, cells_byte_array, "cell_{0}.bin".format(z_slice), file_path)

        poly_binary_array, cell_binary_array = cell_transfer.get_poly_pointer_arrays()
        write_file(feature_folder, poly_binary_array, "poly_pointer_array.bin", file_path)
        write_file(feature_folder, cell_binary_array, "cell_array.bin", file_path)

    log.info(f"Cells binaries generation completed for feature {feature_name}")
    vzg_repacker.log_manifest(f"packed {len(polygon_list)} cells for feature {feature_name}")
    gene_array = vzg_repacker.read_genes_info_array()
    all_genes = list(record["name"] for record in gene_array["transcriptsPerGeneList"])
    seq_genes = identify_sequential(gene_array["transcriptsPerGeneList"], channels)

    matrix_genes = [gene for gene in all_genes if gene not in seq_genes]
    run_dataset_assembling(input_entity_by_gene, feature_folder, vzg_metadata, genes=matrix_genes)

    vzg_repacker.update_genes_info_array(gene_array, seq_genes)
    log.info(f"Assembler data binaries generation complected for feature {feature_name}")


def main_update_vzg(args):
    args = initialize_experimental_args(args)
    validate_args(args)

    vzg_repacker = VzgRepacker(args.input_vzg, args.temp_path)
    log.info("Unpacking vzg file")
    vzg_repacker.unpack_vzg()
    dataset_folder = vzg_repacker.get_dataset_folder()
    gene_array = vzg_repacker.read_genes_info_array()
    vzg_repacker.log_manifest(f"run update-vzg with arguments {args}")

    log.info(f"Dataset folder: {dataset_folder}")
    log.info(f'Number of input genes: {len(gene_array["transcriptsPerGeneList"])}')

    features_folder = os.path.join(dataset_folder, vzg_repacker.features_folder)
    if os.path.exists(features_folder):
        shutil.rmtree(os.path.join(features_folder))

    if not args.input_entity_type:
        args.input_entity_type = read_segmentation_entity_types(args.input_boundaries)

    features = [args.input_entity_type]
    if args.second_boundaries:
        if not args.second_entity_type:
            args.second_entity_type = read_segmentation_entity_types(args.second_boundaries)
        features.append(args.second_entity_type)
        if features[0] == features[1]:
            features[1] = features[1] + "_2"

    if not args.input_metadata:
        args.input_metadata = create_input_metadata(
            vzg_repacker.get_build_temp_folder(), args.input_boundaries, features[0]
        )
    if args.second_boundaries and not args.second_metadata:
        args.second_metadata = create_input_metadata(
            vzg_repacker.get_build_temp_folder(), args.second_boundaries, features[1]
        )

    image_params = load_image_parameters(dataset_folder)
    vzg_repacker.check_update_manifest_genes_info_array(image_params)

    update_feature(
        vzg_repacker, args.input_metadata, args.input_boundaries, args.input_entity_by_gene, image_params, features[0]
    )
    if args.second_boundaries:
        update_feature(
            vzg_repacker,
            args.second_metadata,
            args.second_boundaries,
            args.second_entity_by_gene,
            image_params,
            features[1],
        )

    vzg_repacker.repack_vzg_file(os.path.splitext(args.output_vzg)[0])
    log.info("Update VZG completed")


def parse_args(args: Optional[Sequence[str]] = None) -> argparse.Namespace:
    return get_parser().parse_args(args)
