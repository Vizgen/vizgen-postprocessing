from argparse import ArgumentParser
from dataclasses import dataclass

from vpt.utils.validate import validate_exists, validate_does_not_exist


@dataclass(frozen=True)
class GenerateJsonArgs:
    input_analysis_spec: str
    output_path: str
    overwrite: bool


def validate_args(args: GenerateJsonArgs):
    validate_exists(args.input_analysis_spec)
    if not args.overwrite:
        validate_does_not_exist(args.output_path)


def get_parser() -> ArgumentParser:
    parser = ArgumentParser()

    parser.add_argument('--input-analysis-spec', type=str, required=True,
                        help='Path to a json with analysis arguments for template segmentation specification')
    parser.add_argument('--output-path', type=str, required=True,
                        help='Path to the json file where the generated segmentation specification will be stored')
    parser.add_argument('--overwrite', action='store_true', default=False, required=False,
                        help='')
    return parser


def parse_args():
    return get_parser().parse_args()
