from argparse import ArgumentParser
from dataclasses import dataclass
from typing import Optional

from vpt.convert_geometry.factory import get_conversion_type, SegmentationFileType
from vpt.filesystem import filesystem_path_split
from vpt.utils.output_tools import MIN_ROW_GROUP_SIZE
from vpt.utils.validate import validate_does_not_exist


@dataclass
class ConvertGeometryArgs:
    input_boundaries: str
    output_boundaries: str
    convert_to_3D: bool
    number_z_planes: Optional[int]
    spacing_z_planes: Optional[float]
    output_entity_type: str
    entity_fusion_strategy: str
    id_mapping_file: str
    max_row_group_size: int
    overwrite: bool


def validate_args_with_input(args: ConvertGeometryArgs, input_path: str):
    input_type = get_conversion_type(input_path)
    if input_type in [SegmentationFileType.QPATH, SegmentationFileType.PARQUET]:
        if args.convert_to_3D:
            if args.number_z_planes is None or args.spacing_z_planes is None:
                raise ValueError('To convert 2D segmentation to 3D parquet segmentation the number of z planes '
                                 'and spacing between them should be specified')
            elif args.number_z_planes <= 0:
                raise ValueError('The number of z planes should be positive integer')
            elif args.spacing_z_planes <= 0:
                raise ValueError('The spacing between z planes should be positive')
        else:
            if args.number_z_planes is not None or args.spacing_z_planes is not None:
                raise ValueError('Number of z planes and spacing can be specified only if "--convert-to-3D" argument '
                                 'is passed')

    elif input_type == SegmentationFileType.HDF5:
        if args.convert_to_3D or args.number_z_planes is not None or args.spacing_z_planes is not None:
            raise ValueError('The conversion from 2D hdf5 segmentation to 3D parquet segmentation is not supported')
    else:
        raise ValueError('Type of the passed input file is not supported')


def validate_cmd_args(args: ConvertGeometryArgs):
    if not args.overwrite:
        validate_does_not_exist(args.output_boundaries)
        if args.id_mapping_file:
            validate_does_not_exist(args.id_mapping_file)

    fs, path_inside_fs = filesystem_path_split(args.output_boundaries)
    if fs.exists(path_inside_fs) and not fs.isfile(path_inside_fs):
        raise ValueError('Provided path should be a file')

    if args.max_row_group_size < MIN_ROW_GROUP_SIZE:
        raise ValueError(f'Row group size should be at least {MIN_ROW_GROUP_SIZE}')

    if args.id_mapping_file:
        fs, path_inside_fs = filesystem_path_split(args.id_mapping_file)
        if fs.exists(path_inside_fs) and not fs.isfile(path_inside_fs):
            raise ValueError('Provided path should be a file')


def get_parser():
    parser = ArgumentParser(description='Converts entity boundaries produced by a different tool into a '
                            'vpt compatible parquet file. In the process, each of the input'
                            ' entities is checked for geometric validity, overlap with'
                            ' other geometries, and assigned a globally-unique EntityID '
                            'to facilitate other processing steps.',
                            add_help=False
                            )

    required = parser.add_argument_group('Required arguments')
    required.add_argument('--input-boundaries', type=str, required=True,
                          help='Regular expression that matches all input segmentation files (geojson or hdf5) that '
                               'will be processed.')
    required.add_argument('--output-boundaries', type=str, required=True,
                          help='The path to the parquet file where segmentation compatible with vpt will be saved.')

    opt = parser.add_argument_group('Optional arguments')
    opt.add_argument('--convert-to-3D', action='store_true', default=False, required=False,
                     help='Pass if segmentation should be converted from 2D to 3D by replication. Only possible for '
                          'geojson and parquet input formats.')
    opt.add_argument('--number-z-planes', type=int, default=None, required=False,
                     help='The number of z planes that should be produced during the conversion from 2D to 3D. Should '
                          'be specified only if the "--convert-to-3D" argument is passed')
    opt.add_argument('--spacing-z-planes', type=float, default=None, required=False,
                     help='Step size between z-planes, assuming that z-index 0 is 1 “step” above zero. Should be '
                          'specified only if the "--convert-to-3D" argument is passed')
    opt.add_argument('--output-entity-type', type=str, default='cell',
                     help='String with entity type name. For example: cell, nuclei. Default: cell')
    opt.add_argument('--id-mapping-file', type=str, required=False,
                     help='Path to csv file where map from source segmentation entity id to EntityID in result '
                          'will be saved.')
    opt.add_argument('--entity-fusion-strategy', type=str, default='harmonize',
                     help='String with entity fusion strategy name. One from list: harmonize, union, larger. '
                          'Default: harmonize')
    opt.add_argument('--max-row-group-size', type=int, default=17500, required=False,
                     help=f'Maximum number of rows in row groups inside output parquet files. Cannot be less '
                          f'than {MIN_ROW_GROUP_SIZE}')
    opt.add_argument('--overwrite', action='store_true', default=False, required=False,
                     help='Set flag if you want to use non empty directory and agree that files can be over-written.')
    opt.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    return parser


def parse_cmd_args():
    return get_parser().parse_args()
