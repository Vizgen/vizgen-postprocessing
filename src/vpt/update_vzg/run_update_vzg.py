import argparse

from vpt_core import log

from vpt.derive_cell_metadata.cell_metadata import create_input_metadata
from vpt.update_vzg.cmd_args import UpdateVzgArgs, initialize_experimental_args, validate_args
from vpt.update_vzg.util import clean_up_on_exit, create_workdir
from vpt.update_vzg.vzg import update_vzg
from vpt.update_vzg.vzg2 import update_vzg2
from vpt.utils.input_utils import read_segmentation_entity_types


def _construct_entity_types_list(args: UpdateVzgArgs) -> list:
    features = []

    if args.input_entity_type is None:
        features.append(read_segmentation_entity_types(args.input_boundaries))
    else:
        features.append(args.input_entity_type)

    if args.second_boundaries:
        if args.second_entity_type is None:
            features.append(read_segmentation_entity_types(args.second_boundaries))
        else:
            features.append(args.second_entity_type)

        if features[0] == features[1]:
            features[1] = features[1] + "_2"

    return features


def _create_missing_metadata(args: UpdateVzgArgs, metadata_workdir: str, features: list) -> None:
    if not args.input_metadata:
        args.input_metadata = create_input_metadata(metadata_workdir, args.input_boundaries, features[0])
    if args.second_boundaries and not args.second_metadata:
        args.second_metadata = create_input_metadata(metadata_workdir, args.second_boundaries, features[1])


def main_update_vzg(args_raw: argparse.Namespace):
    args_raw = initialize_experimental_args(args_raw)
    args = UpdateVzgArgs(**vars(args_raw))
    validate_args(args)

    features = _construct_entity_types_list(args)

    with clean_up_on_exit(create_workdir(args.temp_path)) as metadata_workdir:
        _create_missing_metadata(args, metadata_workdir, features)

        if args.input_vzg.endswith(".vzg2"):
            log.info("Format: vzg2")
            update_vzg2(args, features)
        else:
            log.info("Format: vzg")
            update_vzg(args, features)
