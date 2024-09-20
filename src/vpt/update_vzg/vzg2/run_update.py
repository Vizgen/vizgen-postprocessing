import argparse
import os.path

import numpy as np
import pandas as pd
from vpt_core import log
from vpt_core.io.vzgfs import Protocol, filesystem_for_protocol, io_with_retries, protocol_path_split
from vpt_segmentation_packing import assemble_vzg2, pack_cells, preprocess_cells
from vpt_segmentation_packing.data import Feature

from vpt.app.context import current_context, parallel_run
from vpt.app.task import Task
from vpt.update_vzg.cmd_args import UpdateVzgArgs
from vpt.update_vzg.util import clean_up_on_exit, create_workdir
from vpt.update_vzg.vzg2.util import (
    extract_vzg2,
    get_experiment_geometry,
    read_manifest,
    remove_existing_feature_sets,
    update_manifest,
    write_manifest,
)
from vpt.utils.cellsreader import CellsReader, cell_reader_factory


def preprocess_feature_set(args: argparse.Namespace) -> list:
    log.info(f"Feature preprocessing task #{args.task_id} started")
    log.log_system_info()

    cells_reader: CellsReader = cell_reader_factory(args.input_boundaries)

    fovs = list(range(args.task_id, cells_reader.get_fovs_count(), args.total_tasks))

    preprocessed_features = []

    for fov_idx in fovs:
        log.info(f"Preprocessing fov {fov_idx}")
        vpt_features = cells_reader.read_fov(fov_idx)
        vzg2_features = [Feature(feature.id, feature.shapes) for feature in vpt_features]

        preprocessed_features.extend(preprocess_cells(vzg2_features, args.tex_size, args.transform_matrix))

    log.info(f"Feature preprocessing task #{args.task_id} done")
    return preprocessed_features


def pack_feature_set(
    workdir: str,
    metadata_path: str,
    entity_by_gene_path,
    tex_size: tuple,
    transform_matrix: np.ndarray,
    num_z_planes: int,
    feature_set_name: str,
    preprocessed_features: list,
):
    entity_metadata: pd.DataFrame = io_with_retries(metadata_path, "r", lambda f: pd.read_csv(f, index_col=0))
    entity_by_gene: pd.DataFrame = io_with_retries(entity_by_gene_path, "r", lambda f: pd.read_csv(f, index_col=0))

    output_dir = os.path.join(workdir, feature_set_name)

    pack_cells(
        polyList=preprocessed_features,
        cellsDir=output_dir,
        zPlaneCount=num_z_planes,
        texSize=tex_size,
        transformMatrix=transform_matrix,
        cellMetadata=entity_metadata,
        expressionMatrix=entity_by_gene,
    )

    return feature_set_name


def preprocess_and_pack_feature_set(
    workdir: str,
    metadata_path: str,
    boundaries_path: str,
    entity_by_gene_path,
    tex_size: tuple,
    transform_matrix: np.ndarray,
    num_z_planes: int,
    feature_set_name: str,
) -> str:
    log.info(f"Preprocessing features ({feature_set_name})")
    num_processes = current_context().get_workers_count()

    tasks = [
        Task(
            preprocess_feature_set,
            argparse.Namespace(
                input_boundaries=boundaries_path,
                tex_size=tex_size,
                transform_matrix=transform_matrix,
                task_id=i,
                total_tasks=num_processes,
            ),
        )
        for i in range(num_processes)
    ]

    preprocessed_features = []

    for batch in parallel_run(tasks):
        preprocessed_features.extend(batch)

    log.info(f"Packing features ({feature_set_name})")
    return pack_feature_set(
        workdir,
        metadata_path,
        entity_by_gene_path,
        tex_size,
        transform_matrix,
        num_z_planes,
        feature_set_name,
        preprocessed_features,
    )


def reassemble_vzg2(workdir: str, output_path: str) -> None:
    def _assemble(path: str):
        log.info("Started assembling vzg2")
        assemble_vzg2(workdir, path)
        log.info("Finished assembling vzg2")

    protocol, path_inside_fs = protocol_path_split(output_path)

    if protocol == Protocol.LOCAL:
        _assemble(output_path)
        return

    assemble_path = os.path.join(workdir, os.path.basename(output_path))
    _assemble(assemble_path)

    fs = filesystem_for_protocol(protocol)

    log.info(f"Started uploading vzg2 to {output_path}")
    fs.put(assemble_path, path_inside_fs)
    log.info("Finished uploading vzg2")


def update_vzg2(args: UpdateVzgArgs, features: list):
    workdir = create_workdir(args.temp_path)

    with clean_up_on_exit(workdir):
        log.info("Unpacking")
        extract_vzg2(args.input_vzg, workdir)

        log.info("Reading manifest")
        manifest = read_manifest(workdir)

        tex_size, transform_matrix, num_z_planes = get_experiment_geometry(manifest)

        log.info("Removing existing feature sets")
        remove_existing_feature_sets(workdir, manifest)

        feature_paths = []

        log.info("Processing primary feature set")
        feature_paths.append(
            preprocess_and_pack_feature_set(
                workdir,
                args.input_metadata,
                args.input_boundaries,
                args.input_entity_by_gene,
                tex_size,
                transform_matrix,
                num_z_planes,
                features[0],
            )
        )

        if len(features) > 1:
            assert args.second_metadata is not None
            assert args.second_boundaries is not None
            assert args.second_entity_by_gene is not None

            log.info("Processing secondary feature set")
            feature_paths.append(
                preprocess_and_pack_feature_set(
                    workdir,
                    args.second_metadata,
                    args.second_boundaries,
                    args.second_entity_by_gene,
                    tex_size,
                    transform_matrix,
                    num_z_planes,
                    features[1],
                )
            )

        log.info("Updating manifest")
        update_manifest(manifest, features, feature_paths)

        log.info("Saving manifest")
        write_manifest(workdir, manifest)

        log.info("Reassembling vzg2")
        reassemble_vzg2(workdir, args.output_vzg)

        log.info("Cleaning up")

    log.info("Done")
