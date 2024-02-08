import os
from argparse import Namespace

import pytest

from tests.vpt import OUTPUT_FOLDER, TEST_DATA_ROOT
from vpt.generate_segmentation_metrics.main import generate_segmentation_metrics

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
]


@pytest.mark.parametrize("fakesNamespaceArgs", SEG_METRICS_CASES_FAIL)
def test_generate_segmentation_metrics_fail(fakesNamespaceArgs: Namespace):
    with pytest.raises(ValueError):
        generate_segmentation_metrics(fakesNamespaceArgs)
