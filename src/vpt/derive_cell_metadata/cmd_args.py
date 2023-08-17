from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from typing import Optional, Sequence

from vpt.utils.validate import validate_does_not_exist, validate_exists


@dataclass
class DeriveMetadataArgs:
    input_boundaries: str
    output_metadata: str
    input_entity_by_gene: str
    overwrite: bool


def validate_args(args: DeriveMetadataArgs):
    validate_exists(args.input_boundaries)
    if args.input_entity_by_gene:
        validate_exists(args.input_entity_by_gene)
    if not args.overwrite:
        validate_does_not_exist(args.output_metadata)


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Uses the segmentation boundaries to calculate the geometric attributes "
        "of each Entity. These attributes include the position, volume, and morphological features.",
        add_help=False,
    )
    required = parser.add_argument_group("Required arguments")
    required.add_argument(
        "--input-boundaries", required=True, type=str, help="Path to a micron-space parquet boundary file."
    )
    required.add_argument(
        "--output-metadata",
        required=True,
        type=str,
        help="Path to the output csv file where the entity metadata will be stored.",
    )

    opt = parser.add_argument_group("Optional arguments")
    opt.add_argument("--input-entity-by-gene", required=False, type=str, help="Path to an existing entity by gene csv.")
    opt.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        required=False,
        help="Set flag if you want to use non empty directory and agree that files can be over-written.",
    )
    opt.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    return parser


def parse_args(args: Optional[Sequence[str]] = None) -> Namespace:
    return get_parser().parse_args(args)
