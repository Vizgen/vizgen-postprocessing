from argparse import ArgumentParser, Namespace
from typing import Callable

from vpt.compile_tile_segmentation import get_parser as get_compile_tile_segmentation_parser, \
    run as compile_tile_segmentation
from vpt.convert_geometry import get_parser as get_convert_geometry_parser, run_conversion as convert_geometry
from vpt.convert_to_ome import get_parser as get_convert_to_ome_parser, run_ome as convert_to_ome
from vpt.convert_to_ome import get_parser_rgb as get_convert_to_rgb_ome_parser, run_ome_rgb as convert_to_rgb_ome
from vpt.derive_cell_metadata import get_parser as get_derive_cell_metadata_parser, run as derive_cell_metadata
from vpt.partition_transcripts import get_parser as get_partition_transcripts_parser, run as partition_transcripts
from vpt.prepare_segmentation import get_parser as get_prepare_seg_parser, run as prepare_segmentation
from vpt.run_segmentation import get_parser as get_run_segmentation_parser, run as run_segmentation
from vpt.run_segmentation_on_tile import get_parser as get_run_seg_on_tile_parser, run as run_segmentation_on_tile
from vpt.sum_signals import get_parser as get_sum_signals_parser, run as run_sum_signals
from vpt.update_vzg import get_parser as get_update_vzg_parser, run as update_vzg


def get_postprocess_parser() -> ArgumentParser:
    parser = ArgumentParser(description='', usage='vpt [OPTIONS] COMMAND [arguments]', add_help=False,
                            epilog="Run 'vpt COMMAND --help' for more information on a command.")
    parser.add_argument('--processes', type=int, default=1, required=False,
                        help='Number of parallel processes to use when executing locally')
    parser.add_argument('--aws-profile-name', type=str, required=False,
                        help="Named profile for AWS access")
    parser.add_argument('--aws-access-key', type=str, required=False,
                        help="AWS access key from key / secret pair")
    parser.add_argument('--aws-secret-key', type=str, required=False,
                        help="AWS secret from key / secret pair")
    parser.add_argument('--gcs-service-account-key', type=str, required=False,
                        help='Path to a google service account key json file. Not needed if google '
                             'authentication is performed using gcloud')
    parser.add_argument('--verbose', action='store_true', default=False, required=False,
                        help='Display progress messages during execution')
    parser.add_argument('--profile-execution-time', type=str, default=None, required=False,
                        help='Path to profiler output file')
    parser.add_argument('--log-level', type=int, default=1, required=False,
                        help='Log level value. Level is specified as a number from 1 - 5, corresponding '
                             'to debug, info, warning, error, crit')
    parser.add_argument('--log-file', type=str, default=None, required=False,
                        help='Path to log output file. If not provided, logs are written to standard output')
    parser.add_argument("-h", "--help", action="help",
                        help='Show this help message and exit')

    parser._optionals.title = 'Options'
    parser._positionals.title = 'Commands'

    subparsers = parser.add_subparsers(dest='subparser_name', metavar='')

    subparsers.add_parser('run-segmentation', parents=[get_run_segmentation_parser()], add_help=False,
                          help=get_run_segmentation_parser().description,
                          usage='vpt [OPTIONS] run-segmentation [arguments]',
                          description=get_run_segmentation_parser().description)

    subparsers.add_parser('prepare-segmentation', parents=[get_prepare_seg_parser()], add_help=False,
                          help=get_prepare_seg_parser().description,
                          usage='vpt [OPTIONS] prepare-segmentation [arguments]',
                          description=get_prepare_seg_parser().description)

    subparsers.add_parser('run-segmentation-on-tile', parents=[get_run_seg_on_tile_parser()], add_help=False,
                          help=get_run_seg_on_tile_parser().description,
                          usage='vpt [OPTIONS] run-segmentation-on-tile [arguments]',
                          description=get_run_seg_on_tile_parser().description)

    subparsers.add_parser('compile-tile-segmentation', parents=[get_compile_tile_segmentation_parser()], add_help=False,
                          help=get_compile_tile_segmentation_parser().description,
                          usage='vpt [OPTIONS] compile-tile-segmentation [arguments]',
                          description=get_compile_tile_segmentation_parser().description)

    subparsers.add_parser('derive-entity-metadata', parents=[get_derive_cell_metadata_parser()], add_help=False,
                          help=get_derive_cell_metadata_parser().description,
                          usage='vpt [OPTIONS] derive-entity-metadata [arguments]',
                          description=get_derive_cell_metadata_parser().description)

    subparsers.add_parser('partition-transcripts', parents=[get_partition_transcripts_parser()], add_help=False,
                          help=get_partition_transcripts_parser().description,
                          usage='vpt [OPTIONS] partition-transcripts [arguments]',
                          description=get_partition_transcripts_parser().description)

    subparsers.add_parser('sum-signals', parents=[get_sum_signals_parser()], add_help=False,
                          help=get_sum_signals_parser().description,
                          usage='vpt [OPTIONS] sum-signals [arguments]',
                          description=get_sum_signals_parser().description)

    subparsers.add_parser('update-vzg', parents=[get_update_vzg_parser()], add_help=False,
                          help=get_update_vzg_parser().description,
                          usage='vpt [OPTIONS] update-vzg [arguments]',
                          description=get_update_vzg_parser().description)

    subparsers.add_parser('convert-geometry', parents=[get_convert_geometry_parser()], add_help=False,
                          help=get_convert_geometry_parser().description,
                          usage='vpt [OPTIONS] convert-geometry [arguments]',
                          description=get_convert_geometry_parser().description)

    subparsers.add_parser('convert-to-ome', parents=[get_convert_to_ome_parser()], add_help=False,
                          help=get_convert_to_ome_parser().description,
                          usage='vpt [OPTIONS] convert-to-ome [arguments]',
                          description=get_convert_to_ome_parser().description)

    subparsers.add_parser('convert-to-rgb-ome', parents=[get_convert_to_rgb_ome_parser()], add_help=False,
                          help=get_convert_to_rgb_ome_parser().description,
                          usage='vpt [OPTIONS] convert-to-rgb-ome [arguments]',
                          description=get_convert_to_rgb_ome_parser().description)

    return parser


def get_cmd_entrypoint(cmd: str) -> Callable[[Namespace], None]:
    subparsers = {
        'run-segmentation': run_segmentation,
        'prepare-segmentation': prepare_segmentation,
        'run-segmentation-on-tile': run_segmentation_on_tile,
        'compile-tile-segmentation': compile_tile_segmentation,
        'convert-to-ome': convert_to_ome,
        'convert-to-rgb-ome': convert_to_rgb_ome,
        'derive-entity-metadata': derive_cell_metadata,
        'update-vzg': update_vzg,
        'sum-signals': run_sum_signals,
        'partition-transcripts': partition_transcripts,
        'convert-geometry': convert_geometry
    }

    if cmd not in subparsers.keys():
        return lambda x: print(
            "Command or option not recognized. Run 'vpt --help' for more information.")

    return subparsers[cmd]
