from argparse import ArgumentParser
from dataclasses import dataclass

from vpt.utils.validate import validate_exists, validate_does_not_exist
from vpt.filesystem import vzg_open


@dataclass
class PartitionTranscriptsArgs:
    input_boundaries: str
    input_transcripts: str
    output_entity_by_gene: str
    chunk_size: int
    output_transcripts: str
    overwrite: bool


def validate_args(args: PartitionTranscriptsArgs):
    validate_exists(args.input_boundaries)
    validate_exists(args.input_transcripts)

    if not args.overwrite:
        validate_does_not_exist(args.output_entity_by_gene)
        if args.output_transcripts:
            validate_does_not_exist(args.output_transcripts)

    if args.chunk_size <= 0:
        raise ValueError('Chunk size should be a positive integer')

    transcripts_header = {'gene', 'global_x', 'global_y', 'global_z'}
    with vzg_open(args.input_transcripts, 'r') as f:
        header = f.readline()
        header = header.replace('\n', '').split(',')
        if not transcripts_header.issubset(header):
            raise ValueError(f'Expected columns {transcripts_header.difference(header)} were not found in the '
                             f'input-transcripts file. Input transcript file contained columns: {header}')


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(description='Uses the segmentation boundaries to determine which Entity, if any, contains each '
                            'detected transcript. Outputs an Entity by gene matrix, and may optionally output '
                            'a detected transcript csv with an additional column indicating the containing Entity.',
                            add_help=False
                            )
    required = parser.add_argument_group('Required arguments')
    required.add_argument('--input-boundaries', required=True, type=str,
                          help='Path to a micron-space parquet boundary file.')
    required.add_argument('--input-transcripts', required=True, type=str,
                          help='Path to an existing transcripts csv file.')
    required.add_argument('--output-entity-by-gene', required=True, type=str,
                          help='Path to output the Entity by gene matrix csv file.')

    opt = parser.add_argument_group('Optional arguments')
    opt.add_argument('--chunk-size', required=False, type=int, default=10000000,
                     help='Number of transcript file lines to be loaded in memory at once. Default: 10,000,000')
    opt.add_argument('--output-transcripts', required=False, type=str,
                     help='If a filename is provided, a copy of the detected transcripts file will be written '
                     'with an additional column with the EntityID of the cell or other Entity that contains '
                     'each transcript (or -1 if the transcript is not contained by any Entity).')
    opt.add_argument('--overwrite', action='store_true', default=False, required=False,
                     help='Set flag if you want to use non empty directory and agree that files can be over-written.')
    opt.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    return parser


def parse_args():
    return get_parser().parse_args()
