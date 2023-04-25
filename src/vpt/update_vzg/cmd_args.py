from argparse import ArgumentParser
from dataclasses import dataclass
import os

from vpt.utils.validate import validate_exists, validate_does_not_exist, validate_directory_empty

# The maximum number of parallel processes that may be launched by update-vzg
MAX_PROCESSES = 512


@dataclass
class UpdateVzgArgs:
    input_vzg: str
    input_boundaries: str
    input_entity_by_gene: str
    output_vzg: str
    input_metadata: str
    temp_path: str
    overwrite: bool


def validate_args(args: UpdateVzgArgs):
    validate_exists(args.input_vzg)
    validate_exists(args.input_boundaries)
    validate_exists(args.input_entity_by_gene)
    validate_directory_empty(args.temp_path)

    if not args.overwrite:
        validate_does_not_exist(args.output_vzg)


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(description='Updates an existing .vzg file with new segmentation boundaries and the '
                            'corresponding expression matrix. NOTE: This functionality requires '
                            'enough disk space to unpack the existing .vzg file.',
                            add_help=False
                            )

    required = parser.add_argument_group('Required arguments')
    required.add_argument('--input-vzg', required=True, type=str,
                          help='Path to an existing vzg file.')
    required.add_argument('--input-boundaries', required=True, type=str,
                          help='Path to a micron-space parquet boundary file.')
    required.add_argument('--input-entity-by-gene', required=True, type=str,
                          help='Path to the Entity by gene csv file.')
    required.add_argument('--output-vzg', required=True, type=str,
                          help='Path where the updated vzg should be saved.')

    opt = parser.add_argument_group('Optional arguments')
    opt.add_argument('--input-metadata', required=False, type=str,
                     help='Path to an existing entity metadata file.')
    opt.add_argument('--temp-path', required=False, type=str, default=os.path.join(os.getcwd(), 'vzg_build_temp'),
                     help='Path for temporary folder for unzipping vzg file.')
    opt.add_argument('--overwrite', action='store_true', default=False, required=False,
                     help='Set flag if you want to use non empty directory and agree that files can be over-written.')
    opt.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    return parser
