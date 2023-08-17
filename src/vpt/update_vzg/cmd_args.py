import os
from argparse import ArgumentParser
from dataclasses import dataclass
from typing import Optional

from vpt.utils.validate import validate_does_not_exist, validate_exists, validate_experimental

# The maximum number of parallel processes that may be launched by update-vzg
MAX_PROCESSES = 512


@dataclass
class UpdateVzgArgs:
    input_vzg: str
    input_boundaries: str
    second_boundaries: Optional[str]
    input_entity_by_gene: str
    second_entity_by_gene: Optional[str]
    output_vzg: str
    input_metadata: str
    second_metadata: Optional[str]
    input_entity_type: Optional[str]
    second_entity_type: Optional[str]
    temp_path: str
    overwrite: bool


def validate_args(args: UpdateVzgArgs):
    validate_exists(args.input_vzg)
    validate_exists(args.input_boundaries)
    validate_exists(args.input_entity_by_gene)

    if args.second_boundaries is not None:
        if not args.second_entity_by_gene:
            raise ValueError("The Entity by gene csv file for second boundaries should be specified")
        validate_exists(args.second_boundaries)
        validate_exists(args.second_entity_by_gene)
    else:
        if args.second_entity_by_gene is not None:
            raise ValueError(
                "The second boundary file should be specified as the second-entity-by-gene argument is passed"
            )

    if not args.overwrite:
        validate_does_not_exist(args.output_vzg)

    if os.path.exists(args.temp_path) and not os.path.isdir(args.temp_path):
        raise ValueError("The path for the temporary files must specify the directory")


def initialize_experimental_args(args):
    experimental_args = ["second_boundaries", "second_entity_by_gene", "second_metadata", "second_entity_type"]
    for experimental_arg in experimental_args:
        if not hasattr(args, experimental_arg):
            setattr(args, experimental_arg, None)
    return args


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Updates an existing .vzg file with new segmentation boundaries and the "
        "corresponding expression matrix. NOTE: This functionality requires "
        "enough disk space to unpack the existing .vzg file.",
        add_help=False,
    )
    try:
        validate_experimental()
        is_experimental = True
    except NotImplementedError:
        is_experimental = False

    required = parser.add_argument_group("Required arguments")
    required.add_argument("--input-vzg", required=True, type=str, help="Path to an existing vzg file.")
    required.add_argument(
        "--input-boundaries", required=True, type=str, help="Path to a micron-space parquet boundary file."
    )
    required.add_argument(
        "--input-entity-by-gene", required=True, type=str, help="Path to the Entity by gene csv file."
    )
    required.add_argument("--output-vzg", required=True, type=str, help="Path where the updated vzg should be saved.")

    opt = parser.add_argument_group("Optional arguments")
    opt.add_argument("--input-metadata", required=False, type=str, help="Path to an existing entity metadata file.")
    opt.add_argument(
        "--input-entity-type",
        required=False,
        type=str,
        help="Entity type name for detections in input boundaries file.",
    )
    if is_experimental:
        opt.add_argument(
            "--second-boundaries",
            required=False,
            type=str,
            help="Path to a additional micron-space parquet boundary file.",
        )
        opt.add_argument(
            "--second-entity-by-gene",
            required=False,
            type=str,
            help="Path to the Entity by gene csv file for additional boundaries.",
        )
        opt.add_argument(
            "--second-metadata",
            required=False,
            type=str,
            help="Path to an existing entity metadata file for additional boundaries.",
        )
        opt.add_argument(
            "--second-entity-type",
            required=False,
            type=str,
            help="Entity type name for detections in second boundaries file.",
        )
    opt.add_argument(
        "--temp-path",
        required=False,
        type=str,
        default=os.path.join(os.getcwd(), "vzg_build_temp"),
        help="Path for temporary folder for unzipping vzg file.",
    )
    opt.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        required=False,
        help="Set flag if you want to use non empty directory and agree that files can be over-written.",
    )
    opt.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    return parser
