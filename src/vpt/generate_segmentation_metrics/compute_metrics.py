from datetime import datetime
from typing import Any, Dict, List, Tuple, Union

import anndata
import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio
import vpt.generate_segmentation_metrics.metrics_settings as metrics_settings
from pretty_html_table import build_table
from vpt.generate_segmentation_metrics.cmd_args import GenerateSegMetricsArgs
from vpt.generate_segmentation_metrics.output_tools import save_to_parquets
from vpt.utils.input_utils import read_micron_to_mosaic_transform
from vpt_core.io.input_tools import read_parquet
from vpt_core.io.vzgfs import io_with_retries


def total_cell_count(cell_by_gene: pd.DataFrame) -> int:
    num_cells = cell_by_gene.shape[0]
    return round(num_cells, 1)


def cell_volume(cell_metadata: pd.DataFrame) -> Tuple:
    cell_volume_mean = cell_metadata["volume"].mean()
    cell_volume_median = cell_metadata["volume"].median()
    return round(cell_volume_mean, 1), round(cell_volume_median, 1)


def transcripts_per_cell(cell_by_gene: pd.DataFrame) -> Tuple:
    trans_per_cell = cell_by_gene.sum(axis=1).to_numpy()
    trans_per_cell_mean = trans_per_cell.mean()
    trans_per_cell_median = np.median(trans_per_cell)
    return round(trans_per_cell_mean, 1), round(trans_per_cell_median, 1)


def unique_genes_per_cell(cell_by_gene: pd.DataFrame) -> Tuple:
    unique_tpc = np.count_nonzero(cell_by_gene, axis=1)
    unique_tpc_mean = unique_tpc.mean()
    unique_tpc_median = np.median(unique_tpc)
    return round(unique_tpc_mean, 1), round(unique_tpc_median, 1)


def percent_transcripts_in_cell(cell_by_gene: pd.DataFrame, detected_transcripts: pd.DataFrame) -> Union[int, float]:
    transcripts_per_cell = cell_by_gene.sum(axis=1).to_numpy()
    percent_in_cell = transcripts_per_cell.sum() / detected_transcripts.shape[0]
    return round(100 * percent_in_cell, 1)


def area_covered_hq_cells(
    detected_transcripts: pd.DataFrame, m2m_transform: List, cell_polys: gpd.geodataframe.GeoDataFrame
) -> Union[int, float]:
    m2m = np.asarray(m2m_transform, dtype=float)
    num_fovs = np.unique(detected_transcripts["fov"]).shape[0]
    cell_polys["Area"] = cell_polys["Geometry"].area
    area_per_cell_mean = cell_polys.groupby("EntityID")["Area"].mean()
    total_cell_area = area_per_cell_mean.sum()

    fov_dim_px = max(detected_transcripts["x"].max(), detected_transcripts["y"].max())
    fov_dim_um = fov_dim_px / m2m[0][0]
    experimental_area = (fov_dim_um * fov_dim_um) * num_fovs

    experimental_area_covered = total_cell_area / experimental_area
    return round(100 * experimental_area_covered, 1)


def density_low_quality_cells(
    detected_transcripts: pd.DataFrame, m2m_transform: List, num_cells: int, high_quality_cells: int
) -> Union[int, float]:
    low_quality_cells = num_cells - high_quality_cells
    m2m = np.asarray(m2m_transform, dtype=float)
    num_fovs = np.unique(detected_transcripts["fov"]).shape[0]
    fov_dim_px = max(detected_transcripts["x"].max(), detected_transcripts["y"].max())
    fov_dim_um = fov_dim_px / m2m[0][0]
    experimental_area = (fov_dim_um * fov_dim_um) * num_fovs
    density_lq_cells = low_quality_cells / (experimental_area / 1e2)
    return round(density_lq_cells, 2)


def filter_cell_data(
    gdf: gpd.GeoDataFrame,
    cell_by_gene: pd.DataFrame,
    cell_metadata: pd.DataFrame,
    transcript_count_filter_threshold: int,
    volume_filter_threshold: int,
) -> Tuple:
    transcripts_per_cell = cell_by_gene.sum(axis=1).to_numpy()
    tpc_filtered = np.where(transcripts_per_cell >= transcript_count_filter_threshold)[0]
    cv_filtered = np.where(cell_metadata["volume"] >= volume_filter_threshold)[0]
    keeps = np.intersect1d(tpc_filtered, cv_filtered)
    cell_by_gene = cell_by_gene.iloc[keeps]
    cell_metadata = cell_metadata.iloc[keeps]
    gdf = gdf[gdf["EntityID"].isin(cell_metadata.index)]
    return gdf, cell_by_gene, cell_metadata


def make_time() -> str:
    now = datetime.now()

    day_of_week = now.strftime("%A")
    month = now.strftime("%B")
    day = now.strftime("%d")
    hour = now.strftime("%I")
    minute = now.strftime("%M")
    am_pm = now.strftime("%p").lower()
    formatted_date = f"{day_of_week}, {month} {day} at {hour}:{minute}{am_pm}"

    return formatted_date


def make_cells_report_data(extract_args: GenerateSegMetricsArgs, metrics_df: pd.DataFrame, distributions: Dict):
    with open(str(metrics_settings.TEMPLATE_ROOT / "cells_report_template.html"), "r") as template_file:
        output = template_file.read()

    args_dict = {}
    for arg, _ in extract_args.__annotations__.items():
        arg_value = getattr(extract_args, arg)
        args_dict[arg] = arg_value

    args_df = pd.DataFrame(args_dict, index=["Value"])
    args_df.index.name = "Parameter"
    distributions["plot_div19"] = build_table(
        args_df.transpose(),
        "grey_dark",
        index=True,
        font_size="12px",
        font_family="Avenir, sans-serif",
        text_align="left",
    )

    metrics_df.index.name = "Metric"
    distributions["plot_div20"] = build_table(
        metrics_df.transpose(),
        "grey_dark",
        index=True,
        font_size="12px",
        font_family="Avenir, sans-serif",
        text_align="right",
    )

    for fig_name, figure in distributions.items():
        if "div" in fig_name and fig_name not in [
            "plotly_js_only",
            "plot_div16",
            "plot_div19",
            "plot_div20",
            "plot_div7",
            "plot_div8",
            "plot_div9",
            "plot_div10",
            "plot_div12",
            "plot_div13",
            "plot_div14",
        ]:
            distributions[fig_name] = pio.to_html(
                figure,
                include_plotlyjs=False,
                full_html=False,
                config={"displaylogo": False, "responsive": True},
            )

    for name, content in distributions.items():
        output = output.replace("{{ " + name + " }}", content)

    headers = {
        "header0a": f"{metrics_df.loc['All cells', 'Cell count']}",
        "header0b": f"{metrics_df.loc['All cells', 'Transcripts per cell - median']}",
        "header0c": f"{metrics_df.loc['All cells', 'Transcripts within a cell (%)']}",
        "header1": "Input Parameters",
        "header2": "Segmentation Metrics",
        "header3": "Segmentation Preview",
        "header4": "Cell Property Distributions",
        "header5": "Spatial Cell Properties",
        "header6": "UMAPs",
        "header7": "Marker Gene Expression",
        "header8": "Gene Partitioning",
    }
    for header_name, header in headers.items():
        output = output.replace("{{ " + header_name + " }}", header)
    return output


def make_report(cells_report_data: str, extract_args: GenerateSegMetricsArgs):
    with open(str(metrics_settings.TEMPLATE_ROOT / "template.html"), "r") as template_file:
        output = template_file.read()

    output = output.replace("{{ " + "report_name" + " }}", extract_args.experiment_name)
    output = output.replace(
        "{{ " + "experiment_name" + " }}",
        f"VPT Segmentation Report ({extract_args.experiment_name})",
    )
    output = output.replace("{{ " + "time" + " }}", make_time())
    output = output.replace(
        "{{ " + "plotly_js_only" + " }}", px.bar(x=[1], y=[1]).to_html(include_plotlyjs=True, full_html=False)
    )

    output = output.replace("{{ " + "cells_report_data" + " }}", cells_report_data)

    return output


def make_clustering_results(extract_args: GenerateSegMetricsArgs, adata: anndata._core.anndata.AnnData):
    leiden_res = [item for item in adata.obs.columns if item.startswith("leiden")][0]
    cells_categories = pd.DataFrame(
        {
            "EntityID": adata.obs[leiden_res].index.astype("int64"),
            "leiden": adata.obs[leiden_res].astype(str),
        }
    )
    cells_categories = cells_categories.reset_index(drop=True)

    cells_numeric_categories = pd.DataFrame(
        {
            "EntityID": adata.obs["leiden_1.0"].index.astype("int64"),
            "umap_X": adata.obsm["X_umap"][:, 0],
            "umap_Y": adata.obsm["X_umap"][:, 1],
        }
    )
    cells_numeric_categories = cells_numeric_categories.reset_index(drop=True)

    output_dfs = {
        metrics_settings.OUTPUT_FILE_NAME1: cells_categories,
        metrics_settings.OUTPUT_FILE_NAME2: cells_numeric_categories,
    }
    save_to_parquets(output_dfs, extract_args.output_clustering)


def get_metrics(
    cell_polys: gpd.GeoDataFrame,
    cell_polys_filtered: gpd.GeoDataFrame,
    cell_by_gene: pd.DataFrame,
    cell_by_gene_filtered: pd.DataFrame,
    cell_metadata: pd.DataFrame,
    cell_metadata_filtered: pd.DataFrame,
    detected_transcripts: pd.DataFrame,
    m2m_transform: pd.DataFrame,
) -> Tuple[pd.DataFrame, dict]:
    metrics: Dict[str, Any] = {}

    metrics["Cell count"] = total_cell_count(cell_by_gene_filtered)
    (
        metrics["Cell volume - mean (µm³)"],
        metrics["Cell volume - median (µm³)"],
    ) = cell_volume(cell_metadata_filtered)
    (
        metrics["Transcripts per cell - mean"],
        metrics["Transcripts per cell - median"],
    ) = transcripts_per_cell(cell_by_gene_filtered)
    (
        metrics["Unique genes per cell - mean"],
        metrics["Unique genes per cell - median"],
    ) = unique_genes_per_cell(cell_by_gene_filtered)
    metrics["Transcripts within a cell (%)"] = percent_transcripts_in_cell(cell_by_gene_filtered, detected_transcripts)
    metrics["Imaged area covered by cells (%)"] = area_covered_hq_cells(
        detected_transcripts, m2m_transform, cell_polys_filtered
    )
    metrics["Filtered out cell density (1/100µm²)"] = density_low_quality_cells(
        detected_transcripts,
        m2m_transform,
        num_cells=cell_by_gene.shape[0],
        high_quality_cells=cell_by_gene_filtered.shape[0],
    )

    metrics_df = pd.DataFrame(metrics, index=["Cells after filtering", "All cells"])
    cell_volume_all = cell_volume(cell_metadata)
    transcripts_per_cell_all = transcripts_per_cell(cell_by_gene)
    unique_genes_per_cell_all = unique_genes_per_cell(cell_by_gene)
    metrics_df.loc["All cells"] = [
        total_cell_count(cell_by_gene),
        cell_volume_all[0],
        cell_volume_all[1],
        transcripts_per_cell_all[0],
        transcripts_per_cell_all[1],
        unique_genes_per_cell_all[0],
        unique_genes_per_cell_all[1],
        percent_transcripts_in_cell(cell_by_gene, detected_transcripts),
        area_covered_hq_cells(detected_transcripts, m2m_transform, cell_polys),
        density_low_quality_cells(
            detected_transcripts,
            m2m_transform,
            num_cells=cell_by_gene.shape[0],
            high_quality_cells=cell_by_gene.shape[0],
        ),
    ]
    metrics_df = metrics_df.sort_index(level=["All cells", "Cells after filtering"])

    distribution_inputs = {
        "cell_by_gene": cell_by_gene,
        "cell_by_gene_filtered": cell_by_gene_filtered,
        "cell_metadata": cell_metadata,
        "cell_metadata_filtered": cell_metadata_filtered,
        "detected_transcripts": detected_transcripts,
        "cell_polys": cell_polys,
    }

    return metrics_df, distribution_inputs


def compute_metrics(extract_args: GenerateSegMetricsArgs):
    cell_polys = read_parquet(extract_args.input_boundaries)
    cell_by_gene: pd.DataFrame = io_with_retries(
        extract_args.input_entity_by_gene, "r", lambda f: pd.read_csv(f, index_col=0)
    )
    cell_metadata: pd.DataFrame = io_with_retries(
        extract_args.input_metadata, "r", lambda f: pd.read_csv(f, index_col=0)
    )
    detected_transcripts: pd.DataFrame = io_with_retries(extract_args.input_transcripts, "r", lambda f: pd.read_csv(f))
    m2m_transform = read_micron_to_mosaic_transform(extract_args.input_micron_to_mosaic)

    (
        cell_polys_filtered,
        cell_by_gene_filtered,
        cell_metadata_filtered,
    ) = filter_cell_data(
        cell_polys,
        cell_by_gene,
        cell_metadata,
        extract_args.transcript_count_filter_threshold,
        extract_args.volume_filter_threshold,
    )
    return get_metrics(
        cell_polys,
        cell_polys_filtered,
        cell_by_gene,
        cell_by_gene_filtered,
        cell_metadata,
        cell_metadata_filtered,
        detected_transcripts,
        m2m_transform,
    )
