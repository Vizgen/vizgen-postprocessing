from argparse import ArgumentParser
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

import pandas as pd
import geopandas as gpd
from vpt.generate_segmentation_metrics.metrics_settings import OUTPUT_FILE_NAME1, OUTPUT_FILE_NAME2
from vpt.utils.validate import validate_does_not_exist, validate_exists
from vpt_core.io.regex_tools import parse_images_str
from vpt_core.io.vzgfs import filesystem_path_split, io_with_retries


@dataclass
class GenerateSegMetricsArgs:
    input_entity_by_gene: str
    input_metadata: str
    input_transcripts: str
    output_csv: str
    experiment_name: str
    output_report: str
    output_clustering: str
    input_images: str
    input_micron_to_mosaic: str
    input_boundaries: str
    input_z_index: int
    red_stain_name: str
    green_stain_name: str
    blue_stain_name: str
    normalization: str
    transcript_count_filter_threshold: int
    volume_filter_threshold: int
    overwrite: bool


def validate_args(args: GenerateSegMetricsArgs):
    validate_exists(args.input_entity_by_gene)
    validate_exists(args.input_metadata)
    validate_exists(args.input_transcripts)
    validate_exists(args.input_micron_to_mosaic)
    validate_exists(args.input_boundaries)

    if not args.overwrite:
        validate_does_not_exist(args.output_csv)

    if args.output_report is not None and not args.overwrite:
        validate_does_not_exist(args.output_report)

    if args.output_clustering is not None and not args.overwrite:
        fs, path_inside_fs = filesystem_path_split(args.output_clustering)
        if fs.exists(path_inside_fs):
            validate_does_not_exist(args.output_clustering + "/" + OUTPUT_FILE_NAME1)
            validate_does_not_exist(args.output_clustering + "/" + OUTPUT_FILE_NAME2)

    if args.output_report is not None:
        if not args.input_images:
            raise ValueError("Generating an Analysis Report requires specifying input images")

    if args.input_images is not None:
        regex_info_images = parse_images_str(args.input_images)
        image_info: Dict[str, List] = {args.red_stain_name: [], args.green_stain_name: [], args.blue_stain_name: []}
        for image_path in regex_info_images.images:
            if image_path.channel in image_info and image_path.z_layer not in image_info[image_path.channel]:
                image_info[image_path.channel].append(image_path.z_layer)

        for stain, z_s in image_info.items():
            if stain is not None and args.input_z_index not in z_s:
                raise ValueError(
                    f"There is no image with stain: {stain} and z level: {args.input_z_index}. Check spelling or available z index."
                )

    if args.input_z_index < 0:
        raise ValueError("Z index needs to be >= 0")

    if args.transcript_count_filter_threshold < 0:
        raise ValueError("Transcript count threshold needs to be >= 0")

    if args.volume_filter_threshold < 0:
        raise ValueError("Volume threshold needs to be >= 0")

    if not check_entities_exist(args):
        raise ValueError(
            "No Entities meet the threshold criteria: "
            f"transcript-count-filter-threshold: {args.transcript_count_filter_threshold} and "
            f"volume-filter-threshold: {args.volume_filter_threshold}"
        )

    acceptable_filters = ["none", "range", "clahe"]
    if args.normalization.lower() not in acceptable_filters:
        raise ValueError(f"{args.normalization} is not currently a supported normalization type")


def check_entities_exist(args: GenerateSegMetricsArgs) -> bool:
    # Importing filter_cell_data function here to avoid circular import during module initailization
    from vpt.generate_segmentation_metrics.compute_metrics import filter_cell_data

    cell_polys = gpd.GeoDataFrame(columns=["EntityID"])
    cell_by_gene: pd.DataFrame = io_with_retries(args.input_entity_by_gene, "r", lambda f: pd.read_csv(f, index_col=0))
    cell_metadata: pd.DataFrame = io_with_retries(args.input_metadata, "r", lambda f: pd.read_csv(f, index_col=0))
    _, _, cell_metadata_filtered = filter_cell_data(
        cell_polys, cell_by_gene, cell_metadata, args.transcript_count_filter_threshold, args.volume_filter_threshold
    )
    return len(cell_metadata_filtered) > 0


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Computes a number of segmentation metrics and figures "
        "to assess the quality of cell segmentation",
        add_help=False,
    )

    required = parser.add_argument_group("Required arguments")
    required.add_argument(
        "--input-entity-by-gene",
        required=True,
        type=str,
        help="Path to the Entity by gene csv file.",
    )
    required.add_argument(
        "--input-metadata",
        required=True,
        type=str,
        help="Path to the output csv file where the entity metadata will be stored.",
    )
    required.add_argument(
        "--input-transcripts",
        required=True,
        type=str,
        help="Path to an existing transcripts csv file.",
    )
    required.add_argument(
        "--input-boundaries",
        required=True,
        type=str,
        help="Path to a micron-space parquet boundary file.",
    )
    required.add_argument(
        "--input-micron-to-mosaic",
        required=True,
        type=str,
        help="Path to the micron to mosaic pixel transformation matrix.",
    )
    required.add_argument(
        "--output-csv",
        type=str,
        required=True,
        help="Path to the csv file where segmentation metrics will be stored.",
    )

    opt = parser.add_argument_group("Optional arguments")
    opt.add_argument(
        "--input-images",
        type=str,
        help="Input images can be specified in one of three ways: 1. The path to a directory of tiff files, "
        "if the files are named by the MERSCOPE convention. Example: /path/to/files/ 2. The path to a "
        "directory of tiff files including a python formatting string specifying the file name. The "
        'format string must specify values for "stain" and "z". Example: '
        "/path/to/files/image_{stain}_z{z}.tif 3. A regular expression matching the tiff files to be "
        'used, where the regular expression specifies values for "stain" and "z". Example: '
        r"/path/to/files/mosaic_(?P<stain>[\w|-]+)_z(?P<z>[0-9]+).tif In all cases, the values for "
        '"stain" and "z" must match the stains and z indexes specified in the segmentation algorithm.',
    )
    opt.add_argument(
        "--experiment-name",
        type=str,
        default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        help="The name of the experiment to be used as the index in the output csv and segmentation report. "
        "Default: Analysis Timestamp.",
    )
    opt.add_argument(
        "--output-report",
        type=str,
        default=None,
        help="Path to the output HTML file, will append .html to the end if not included in file name.",
    )
    opt.add_argument(
        "--output-clustering",
        type=str,
        default=None,
        help="Path where the Cell categories Parquet files with clustering results will be saved.",
    )
    opt.add_argument(
        "--input-z-index",
        type=int,
        default=2,
        help="The Z plane of the mosaic tiff images to use for the patch. Default: 2.",
    )
    opt.add_argument(
        "--red-stain-name",
        type=str,
        default=None,
        help="The name of the stain that will be used for the red channel in images. Default: None.",
    )
    opt.add_argument(
        "--green-stain-name",
        type=str,
        default="PolyT",
        help="The name of the stain that will be used for the red channel in images. Default: PolyT.",
    )
    opt.add_argument(
        "--blue-stain-name",
        type=str,
        default="DAPI",
        help="The name of the stain that will be used for the blue channel in images. Default: DAPI.",
    )
    opt.add_argument(
        "--normalization",
        type=str,
        default="CLAHE",
        help="The name of the normalization method that will be used on each channel. Default: CLAHE.",
    )
    opt.add_argument(
        "--transcript-count-filter-threshold",
        type=int,
        default=100,
        help="The cell transcript count threshold used for computing metrics and clustering. Default: 100.",
    )
    opt.add_argument(
        "--volume-filter-threshold",
        type=int,
        default=200,
        help="The cell volume threshold used for computing metrics and clustering. Default: 200.",
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
