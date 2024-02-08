import argparse
import warnings

from vpt.generate_segmentation_metrics.cluster_data import cluster_data
from vpt.generate_segmentation_metrics.cmd_args import GenerateSegMetricsArgs, get_parser, validate_args
from vpt.generate_segmentation_metrics.compute_metrics import (
    compute_metrics,
    make_cells_report_data,
    make_clustering_results,
    make_report,
)
from vpt.generate_segmentation_metrics.distributions import Distributions
from vpt.generate_segmentation_metrics.output_tools import make_parent_folder
from vpt.generate_segmentation_metrics.metrics_settings import METRICS_CSV_OUTPUT_MAPPER
from vpt.utils.process_patch import make_html
from vpt_core import log
from vpt_core.io.vzgfs import initialize_filesystem, io_with_retries

warnings.filterwarnings("ignore")


def generate_segmentation_metrics(args: argparse.Namespace):
    extract_args = GenerateSegMetricsArgs(**vars(args))
    validate_args(extract_args)
    log.info("Generate segmentation metrics started")

    metrics_df, distribution_inputs = compute_metrics(extract_args)
    make_parent_folder(extract_args.output_csv)
    io_with_retries(
        extract_args.output_csv,
        "w",
        metrics_df.rename(columns=METRICS_CSV_OUTPUT_MAPPER).to_csv,
    )

    if extract_args.output_clustering or extract_args.output_report:
        log.info("Cell clustering started")
        cluster_ann = cluster_data(
            distribution_inputs["cell_by_gene_filtered"],
            distribution_inputs["cell_metadata_filtered"],
        )
        log.info("Cell clustering finished")

    if extract_args.output_report:
        log.info("Making html report started")
        distribution_inputs["extract_args"] = extract_args
        distribution_inputs["cluster_ann"] = cluster_ann
        dist = Distributions(distribution_inputs)
        distributions = dist.make_distributions()
        cells_report_data = make_cells_report_data(extract_args, metrics_df, distributions)
        html_string = make_report(cells_report_data, extract_args)
        io_with_retries(
            make_html(extract_args.output_report),
            "w",
            lambda f: f.write(html_string),
            encoding="utf-8",
        )
        log.info("Making html report finished")

    if extract_args.output_clustering:
        make_clustering_results(extract_args, cluster_ann)

    log.info("Generate segmentation metrics finished")


if __name__ == "__main__":
    initialize_filesystem()
    generate_segmentation_metrics(get_parser().parse_args())
