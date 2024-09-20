import os
from argparse import Namespace

import pandas as pd
import pytest
import scanpy as sc
from vpt_core.io.input_tools import read_parquet
from vpt_core.io.vzgfs import io_with_retries

from tests.vpt import OUTPUT_FOLDER, TEST_DATA_ROOT
from vpt.generate_segmentation_metrics.cmd_args import GenerateSegMetricsArgs
from vpt.generate_segmentation_metrics.distributions import Distributions
from vpt.generate_segmentation_metrics.distributions_utils import make_empty_anndata
from vpt.generate_segmentation_metrics.main import generate_segmentation_metrics
from vpt.generate_segmentation_metrics.metrics_settings import MAX_ROWS

SEG_METRICS_CASES = [
    Namespace(
        input_entity_by_gene=str(TEST_DATA_ROOT / "smallset" / "cell_by_gene.csv"),
        input_metadata=str(TEST_DATA_ROOT / "smallset" / "cell_metadata.csv"),
        input_transcripts=str(TEST_DATA_ROOT / "smallset" / "detected_transcripts_downsampled.csv"),
        output_csv=str(OUTPUT_FOLDER / "test.csv"),
        experiment_name="smallset",
        output_report=None,
        output_clustering=None,
        input_images=str(TEST_DATA_ROOT / "smallset" / "images"),
        input_boundaries=str(TEST_DATA_ROOT / "smallset" / "cell_micron_space.parquet"),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "smallset" / "micron_to_mosaic_pixel_transform.csv"),
        input_z_index=0,
        red_stain_name="Cellbound1",
        green_stain_name="Cellbound3",
        blue_stain_name="DAPI",
        normalization="clahe",
        transcript_count_filter_threshold=0,
        volume_filter_threshold=0,
        overwrite=True,
    ),
    Namespace(
        input_entity_by_gene=str(TEST_DATA_ROOT / "smallset" / "cell_by_gene.csv"),
        input_metadata=str(TEST_DATA_ROOT / "smallset" / "cell_metadata.csv"),
        input_transcripts=str(TEST_DATA_ROOT / "smallset" / "detected_transcripts_downsampled.csv"),
        output_csv=str(OUTPUT_FOLDER / "test.csv"),
        experiment_name="smallset",
        output_report=str(OUTPUT_FOLDER / "test.html"),
        output_clustering=str(OUTPUT_FOLDER),
        input_images=str(TEST_DATA_ROOT / "smallset" / "images"),
        input_boundaries=str(TEST_DATA_ROOT / "smallset" / "cell_micron_space.parquet"),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "smallset" / "micron_to_mosaic_pixel_transform.csv"),
        input_z_index=0,
        red_stain_name="Cellbound1",
        green_stain_name="Cellbound3",
        blue_stain_name="DAPI",
        normalization="clahe",
        transcript_count_filter_threshold=0,
        volume_filter_threshold=0,
        overwrite=True,
    ),
    Namespace(
        input_entity_by_gene=str(TEST_DATA_ROOT / "smallset" / "cell_by_gene.csv"),
        input_metadata=str(TEST_DATA_ROOT / "smallset" / "cell_metadata.csv"),
        input_transcripts=str(TEST_DATA_ROOT / "smallset" / "detected_transcripts_downsampled.csv"),
        output_csv=str(OUTPUT_FOLDER / "test.csv"),
        experiment_name="smallset",
        output_report=str(OUTPUT_FOLDER / "test.html"),
        output_clustering=str(OUTPUT_FOLDER),
        input_images=str(TEST_DATA_ROOT / "smallset" / "images"),
        input_boundaries=str(TEST_DATA_ROOT / "smallset" / "cell_micron_space.parquet"),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "smallset" / "micron_to_mosaic_pixel_transform.csv"),
        input_z_index=0,
        red_stain_name=None,
        green_stain_name="Cellbound3",
        blue_stain_name="DAPI",
        normalization="clahe",
        transcript_count_filter_threshold=0,
        volume_filter_threshold=0,
        overwrite=True,
    ),
    Namespace(
        input_entity_by_gene=str(TEST_DATA_ROOT / "smallset" / "cell_by_gene.csv"),
        input_metadata=str(TEST_DATA_ROOT / "smallset" / "cell_metadata.csv"),
        input_transcripts=str(TEST_DATA_ROOT / "smallset" / "detected_transcripts_downsampled.csv"),
        output_csv=str(OUTPUT_FOLDER / "test.csv"),
        experiment_name="smallset",
        output_report=None,
        output_clustering=None,
        input_images=None,
        input_boundaries=str(TEST_DATA_ROOT / "smallset" / "cell_micron_space.parquet"),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "smallset" / "micron_to_mosaic_pixel_transform.csv"),
        input_z_index=0,
        red_stain_name=None,
        green_stain_name="PolyT",
        blue_stain_name="DAPI",
        normalization="clahe",
        transcript_count_filter_threshold=0,
        volume_filter_threshold=0,
        overwrite=True,
    ),
]


@pytest.mark.parametrize("fakesNamespaceArgs", SEG_METRICS_CASES)
def test_generate_segmentation_metrics(fakesNamespaceArgs: Namespace):
    generate_segmentation_metrics(fakesNamespaceArgs)
    assert os.path.exists(fakesNamespaceArgs.output_csv)

    if os.path.exists(fakesNamespaceArgs.output_csv):
        os.remove(fakesNamespaceArgs.output_csv)

    if fakesNamespaceArgs.output_report:
        assert os.path.exists(fakesNamespaceArgs.output_report)
        if os.path.exists(fakesNamespaceArgs.output_report):
            os.remove(fakesNamespaceArgs.output_report)

    if fakesNamespaceArgs.output_clustering:
        assert os.path.exists(os.path.join(fakesNamespaceArgs.output_clustering, "Cells_categories.parquet"))
        assert os.path.exists(os.path.join(fakesNamespaceArgs.output_clustering, "Cells_numeric_categories.parquet"))
        if os.path.exists(os.path.join(fakesNamespaceArgs.output_clustering, "Cells_categories.parquet")):
            os.remove(os.path.join(fakesNamespaceArgs.output_clustering, "Cells_categories.parquet"))
        if os.path.exists(os.path.join(fakesNamespaceArgs.output_clustering, "Cells_numeric_categories.parquet")):
            os.remove(
                os.path.join(
                    fakesNamespaceArgs.output_clustering,
                    "Cells_numeric_categories.parquet",
                )
            )


SEG_METRICS_CASES_FAIL = [
    Namespace(
        input_entity_by_gene=str(TEST_DATA_ROOT / "smallset" / "cell_by_gene.csv"),
        input_metadata=str(TEST_DATA_ROOT / "smallset" / "cell_metadata.csv"),
        input_transcripts=str(TEST_DATA_ROOT / "smallset" / "detected_transcripts_downsampled.csv"),
        output_csv=str(OUTPUT_FOLDER / "test.csv"),
        experiment_name="smallset",
        output_report=str(OUTPUT_FOLDER / "test.html"),
        output_clustering=str(OUTPUT_FOLDER),
        input_images=str(TEST_DATA_ROOT / "smallset" / "images"),
        input_boundaries=str(TEST_DATA_ROOT / "smallset" / "cell_micron_space.parquet"),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "smallset" / "micron_to_mosaic_pixel_transform.csv"),
        input_z_index=-1,
        red_stain_name="Cellbound1",
        green_stain_name="Cellbound3",
        blue_stain_name="DAPI",
        normalization="clahe",
        transcript_count_filter_threshold=0,
        volume_filter_threshold=0,
        overwrite=True,
    ),
    Namespace(
        input_entity_by_gene=str(TEST_DATA_ROOT / "smallset" / "cell_by_gene.csv"),
        input_metadata=str(TEST_DATA_ROOT / "smallset" / "cell_metadata.csv"),
        input_transcripts=str(TEST_DATA_ROOT / "smallset" / "detected_transcripts_downsampled.csv"),
        output_csv=str(OUTPUT_FOLDER / "test.csv"),
        experiment_name="smallset",
        output_report=str(OUTPUT_FOLDER / "test.html"),
        output_clustering=str(OUTPUT_FOLDER),
        input_images=str(TEST_DATA_ROOT / "smallset" / "images"),
        input_boundaries=str(TEST_DATA_ROOT / "smallset" / "cell_micron_space.parquet"),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "smallset" / "micron_to_mosaic_pixel_transform.csv"),
        input_z_index=0,
        red_stain_name="Cellbound1",
        green_stain_name="Cellbound3",
        blue_stain_name="DAPI",
        normalization="clahe",
        transcript_count_filter_threshold=-1,
        volume_filter_threshold=0,
        overwrite=True,
    ),
    Namespace(
        input_entity_by_gene=str(TEST_DATA_ROOT / "smallset" / "cell_by_gene.csv"),
        input_metadata=str(TEST_DATA_ROOT / "smallset" / "cell_metadata.csv"),
        input_transcripts=str(TEST_DATA_ROOT / "smallset" / "detected_transcripts_downsampled.csv"),
        output_csv=str(OUTPUT_FOLDER / "test.csv"),
        experiment_name="smallset",
        output_report=str(OUTPUT_FOLDER / "test.html"),
        output_clustering=str(OUTPUT_FOLDER),
        input_images=str(TEST_DATA_ROOT / "smallset" / "images"),
        input_boundaries=str(TEST_DATA_ROOT / "smallset" / "cell_micron_space.parquet"),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "smallset" / "micron_to_mosaic_pixel_transform.csv"),
        input_z_index=0,
        red_stain_name="Cellbound1",
        green_stain_name="Cellbound3",
        blue_stain_name="DAPI",
        normalization="clahe",
        transcript_count_filter_threshold=0,
        volume_filter_threshold=-1,
        overwrite=True,
    ),
    Namespace(
        input_entity_by_gene=str(TEST_DATA_ROOT / "smallset" / "cell_by_gene.csv"),
        input_metadata=str(TEST_DATA_ROOT / "smallset" / "cell_metadata.csv"),
        input_transcripts=str(TEST_DATA_ROOT / "smallset" / "detected_transcripts_downsampled.csv"),
        output_csv=str(OUTPUT_FOLDER / "test.csv"),
        experiment_name="smallset",
        output_report=str(OUTPUT_FOLDER / "test.html"),
        output_clustering=str(OUTPUT_FOLDER),
        input_images=str(TEST_DATA_ROOT / "smallset" / "images"),
        input_boundaries=str(TEST_DATA_ROOT / "smallset" / "cell_micron_space.parquet"),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "smallset" / "micron_to_mosaic_pixel_transform.csv"),
        input_z_index=0,
        red_stain_name="Cellbound1",
        green_stain_name="Cellbound3",
        blue_stain_name="DAPI",
        normalization="blur",
        transcript_count_filter_threshold=0,
        volume_filter_threshold=0,
        overwrite=True,
    ),
    Namespace(
        input_entity_by_gene=str(TEST_DATA_ROOT / "smallset" / "cell_by_gene.csv"),
        input_metadata=str(TEST_DATA_ROOT / "smallset" / "cell_metadata.csv"),
        input_transcripts=str(TEST_DATA_ROOT / "smallset" / "detected_transcripts_downsampled.csv"),
        output_csv=str(OUTPUT_FOLDER / "test.csv"),
        experiment_name="smallset",
        output_report=str(OUTPUT_FOLDER / "test.html"),
        output_clustering=str(OUTPUT_FOLDER),
        input_images=str(TEST_DATA_ROOT / "smallset" / "images"),
        input_boundaries=str(TEST_DATA_ROOT / "smallset" / "cell_micron_space.parquet"),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "smallset" / "micron_to_mosaic_pixel_transform.csv"),
        input_z_index=7,
        red_stain_name="Cellbound1",
        green_stain_name="Cellbound3",
        blue_stain_name="DAPI",
        normalization="clahe",
        transcript_count_filter_threshold=0,
        volume_filter_threshold=0,
        overwrite=True,
    ),
    Namespace(
        input_entity_by_gene=str(TEST_DATA_ROOT / "smallset" / "cell_by_gene.csv"),
        input_metadata=str(TEST_DATA_ROOT / "smallset" / "cell_metadata.csv"),
        input_transcripts=str(TEST_DATA_ROOT / "smallset" / "detected_transcripts_downsampled.csv"),
        output_csv=str(OUTPUT_FOLDER / "test.csv"),
        experiment_name="smallset",
        output_report=str(OUTPUT_FOLDER / "test.html"),
        output_clustering=str(OUTPUT_FOLDER),
        input_images=str(TEST_DATA_ROOT / "smallset" / "images"),
        input_boundaries=str(TEST_DATA_ROOT / "smallset" / "cell_micron_space.parquet"),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "smallset" / "micron_to_mosaic_pixel_transform.csv"),
        input_z_index=0,
        red_stain_name="Cellbound1",
        green_stain_name="PolyT",
        blue_stain_name="DAPI",
        normalization="clahe",
        transcript_count_filter_threshold=0,
        volume_filter_threshold=0,
        overwrite=True,
    ),
    Namespace(
        input_entity_by_gene=str(TEST_DATA_ROOT / "smallset" / "cell_by_gene.csv"),
        input_metadata=str(TEST_DATA_ROOT / "smallset" / "cell_metadata.csv"),
        input_transcripts=str(TEST_DATA_ROOT / "smallset" / "detected_transcripts_downsampled.csv"),
        output_csv=str(OUTPUT_FOLDER / "test.csv"),
        experiment_name="smallset",
        output_report=str(OUTPUT_FOLDER / "test.html"),
        output_clustering=str(OUTPUT_FOLDER),
        input_images="",
        input_boundaries=str(TEST_DATA_ROOT / "smallset" / "cell_micron_space.parquet"),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "smallset" / "micron_to_mosaic_pixel_transform.csv"),
        input_z_index=0,
        red_stain_name="Cellbound1",
        green_stain_name="Cellbound3",
        blue_stain_name="DAPI",
        normalization="clahe",
        transcript_count_filter_threshold=0,
        volume_filter_threshold=0,
        overwrite=True,
    ),
    Namespace(
        input_entity_by_gene=str(TEST_DATA_ROOT / "smallset" / "cell_by_gene_empty.csv"),
        input_metadata=str(TEST_DATA_ROOT / "smallset" / "cell_metadata_empty.csv"),
        input_transcripts=str(TEST_DATA_ROOT / "smallset" / "detected_transcripts_downsampled.csv"),
        output_csv=str(OUTPUT_FOLDER / "test.csv"),
        experiment_name="smallset",
        output_report=str(OUTPUT_FOLDER / "test.html"),
        output_clustering=None,
        input_images=str(TEST_DATA_ROOT / "smallset" / "images"),
        input_boundaries=str(TEST_DATA_ROOT / "smallset" / "cell_micron_space.parquet"),
        input_micron_to_mosaic=str(TEST_DATA_ROOT / "smallset" / "micron_to_mosaic_pixel_transform.csv"),
        input_z_index=0,
        red_stain_name="Cellbound1",
        green_stain_name="Cellbound3",
        blue_stain_name="DAPI",
        normalization="clahe",
        transcript_count_filter_threshold=0,
        volume_filter_threshold=0,
        overwrite=True,
    ),
]


@pytest.mark.parametrize("fakesNamespaceArgs", SEG_METRICS_CASES_FAIL)
def test_generate_segmentation_metrics_fail(fakesNamespaceArgs: Namespace):
    with pytest.raises(ValueError):
        generate_segmentation_metrics(fakesNamespaceArgs)


ARGS = Namespace(
    input_entity_by_gene=str(TEST_DATA_ROOT / "smallset" / "cell_by_gene.csv"),
    input_metadata=str(TEST_DATA_ROOT / "smallset" / "cell_metadata.csv"),
    input_transcripts=str(TEST_DATA_ROOT / "smallset" / "detected_transcripts_downsampled.csv"),
    output_csv=str(OUTPUT_FOLDER / "test.csv"),
    experiment_name="smallset",
    output_report=str(OUTPUT_FOLDER / "test.html"),
    output_clustering=None,
    input_images=str(TEST_DATA_ROOT / "smallset" / "images"),
    input_boundaries=str(TEST_DATA_ROOT / "smallset" / "cell_micron_space.parquet"),
    input_micron_to_mosaic=str(TEST_DATA_ROOT / "smallset" / "micron_to_mosaic_pixel_transform.csv"),
    input_z_index=0,
    red_stain_name="Cellbound1",
    green_stain_name="Cellbound3",
    blue_stain_name="DAPI",
    normalization="clahe",
    transcript_count_filter_threshold=0,
    volume_filter_threshold=0,
    overwrite=True,
)


def test_make_distributions() -> None:
    extract_args = GenerateSegMetricsArgs(**vars(ARGS))
    distribution_inputs = {
        "extract_args": extract_args,
        "cell_by_gene": io_with_retries(extract_args.input_entity_by_gene, "r", lambda f: pd.read_csv(f, index_col=0)),
        "cell_by_gene_filtered": io_with_retries(
            extract_args.input_entity_by_gene, "r", lambda f: pd.read_csv(f, index_col=0)
        ),
        "cell_metadata": io_with_retries(extract_args.input_metadata, "r", lambda f: pd.read_csv(f, index_col=0)),
        "cell_metadata_filtered": io_with_retries(
            extract_args.input_metadata, "r", lambda f: pd.read_csv(f, index_col=0)
        ),
        "cluster_ann": sc.read_h5ad(str(TEST_DATA_ROOT / "smallset" / "cluster_ann.hdf5")),
        "detected_transcripts": io_with_retries(extract_args.input_transcripts, "r", lambda f: pd.read_csv(f)),
        "cell_polys": read_parquet(extract_args.input_boundaries),
    }
    dist = Distributions(distribution_inputs)
    dist.make_distributions()
    assert len(dist.distributions) > 0


def test_cluster_data_fail() -> None:
    extract_args = GenerateSegMetricsArgs(**vars(ARGS))
    distribution_inputs = {
        "extract_args": extract_args,
        "cell_by_gene": io_with_retries(extract_args.input_entity_by_gene, "r", lambda f: pd.read_csv(f, index_col=0)),
        "cell_by_gene_filtered": io_with_retries(
            extract_args.input_entity_by_gene, "r", lambda f: pd.read_csv(f, index_col=0)
        ),
        "cell_metadata": io_with_retries(extract_args.input_metadata, "r", lambda f: pd.read_csv(f, index_col=0)),
        "cell_metadata_filtered": io_with_retries(
            extract_args.input_metadata, "r", lambda f: pd.read_csv(f, index_col=0)
        ),
        "cluster_ann": None,
        "detected_transcripts": io_with_retries(extract_args.input_transcripts, "r", lambda f: pd.read_csv(f)),
        "cell_polys": read_parquet(extract_args.input_boundaries),
    }
    distribution_inputs["cluster_ann"] = make_empty_anndata(len(distribution_inputs["cell_metadata_filtered"]))
    distribution_inputs["cluster_ann"].obs.index = distribution_inputs["cell_metadata_filtered"].index
    assert len(distribution_inputs["cluster_ann"]) > 0
    dist = Distributions(distribution_inputs)
    dist.make_distributions()
    assert len(dist.distributions) > 0


def test_downsample_anndata() -> None:
    extract_args = GenerateSegMetricsArgs(**vars(ARGS))
    distribution_inputs = {
        "extract_args": extract_args,
        "cell_by_gene": pd.DataFrame(0, index=range(MAX_ROWS + 10), columns=["center_x", "center_y"]),
        "cell_by_gene_filtered": pd.DataFrame(0, index=range(MAX_ROWS + 10), columns=["center_x", "center_y"]),
        "cell_metadata": pd.DataFrame(0, index=range(MAX_ROWS + 10), columns=["center_x", "center_y"]),
        "cell_metadata_filtered": pd.DataFrame(0, index=range(MAX_ROWS + 10), columns=["center_x", "center_y"]),
        "cluster_ann": None,
        "detected_transcripts": io_with_retries(extract_args.input_transcripts, "r", lambda f: pd.read_csv(f)),
        "cell_polys": read_parquet(extract_args.input_boundaries),
    }
    assert len(distribution_inputs["cell_metadata"] > MAX_ROWS)
    distribution_inputs["cluster_ann"] = make_empty_anndata(len(distribution_inputs["cell_metadata_filtered"]))
    distribution_inputs["cluster_ann"].obs.index = distribution_inputs["cell_metadata_filtered"].index
    dist = Distributions(distribution_inputs)
    assert len(dist.sampled_indices) == MAX_ROWS
