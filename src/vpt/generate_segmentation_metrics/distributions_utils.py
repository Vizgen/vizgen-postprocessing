import base64
import os
import tempfile
import warnings
from argparse import Namespace
from typing import Union

import anndata
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import scanpy as sc
import shapely
from matplotlib.colors import Colormap
from shapely import geometry
from vpt_core.io.regex_tools import parse_images_str
from wrapt_timeout_decorator import timeout

from vpt.generate_segmentation_metrics.cmd_args import GenerateSegMetricsArgs
from vpt.generate_segmentation_metrics.metrics_settings import PLOT_RENDERING_TIMEOUT
from vpt.utils.input_utils import read_micron_to_mosaic_transform
from vpt.utils.process_patch import ExtractImageArgs, transform_coords

warnings.filterwarnings("ignore")


def convert_args(
    extract_args: GenerateSegMetricsArgs,
    center_x: float,
    center_y: float,
    size_x: float,
    size_y: float,
) -> ExtractImageArgs:
    m2m_transform = (
        extract_args.m2m_transform
        if hasattr(extract_args, "m2m_transform")
        else read_micron_to_mosaic_transform(extract_args.input_micron_to_mosaic)
    )
    images = extract_args.images if hasattr(extract_args, "images") else parse_images_str(extract_args.input_images)

    args = Namespace(
        images=images,
        m2m_transform=m2m_transform,
        center_x=center_x,
        center_y=center_y,
        green_stain_name=extract_args.green_stain_name,
        output_patch="",
        size_x=size_x,
        size_y=size_y,
        input_z_index=extract_args.input_z_index,
        red_stain_name=extract_args.red_stain_name,
        blue_stain_name=extract_args.blue_stain_name,
        normalization="CLAHE",
        overwrite=False,
    )
    extract_args_converted = ExtractImageArgs(**vars(args))
    return extract_args_converted


def crop_segmentation(
    extract_args_converted: ExtractImageArgs, gdf: gpd.geodataframe.GeoDataFrame
) -> gpd.geodataframe.GeoDataFrame:
    m2m_transform = np.asarray(extract_args_converted.m2m_transform, dtype=float)
    window_micron = [
        extract_args_converted.center_x,
        extract_args_converted.center_y,
        extract_args_converted.size_x,
        extract_args_converted.size_y,
    ]
    window_mosaic = transform_coords(extract_args_converted)
    bounding_box = geometry.box(
        minx=window_micron[0] - (window_micron[2] / 2),
        miny=window_micron[1] - (window_micron[3] / 2),
        maxx=window_micron[0] + (window_micron[2] / 2),
        maxy=window_micron[1] + (window_micron[3] / 2),
    )
    cell_polys = gdf[gdf["Geometry"].within(bounding_box)]
    cell_polys["Geometry"] = cell_polys["Geometry"].apply(
        lambda p: shapely.affinity.scale(
            p,
            m2m_transform[0, 0],
            m2m_transform[1, 1],
            origin=(window_micron[0], window_micron[1]),
        )
    )
    cell_polys["Geometry"] = cell_polys["Geometry"].apply(
        lambda p: shapely.affinity.translate(
            p,
            -window_micron[0] + (window_mosaic[2] / 2),
            -window_micron[1] + (window_mosaic[3] / 2),
        )
    )

    return cell_polys


def make_dotplot(
    adata: anndata._core.anndata.AnnData, cmap: Union[str, Colormap] = "Blues"
) -> sc.plotting._dotplot.DotPlot:
    leiden_res = [item for item in adata.obs.columns if item.startswith("leiden")][0]

    # If a cluster only has 1 cell, the descriptive stats needed for the dotplot will fail
    cluster_counts = adata.obs.groupby(leiden_res).count()
    clusters_with_enough_cells = list(cluster_counts.loc[cluster_counts["volume"] > 1].index)

    # If there are no cells to cluster or there are no clusters with enough cells, the dotplot creation will fail
    if "empty_anndata_indicator" in adata.uns or len(clusters_with_enough_cells) == 0:
        dotplot = plt.figure(figsize=(5, 5))
        message = "There aren't any clusters with enough cells to construct a dotplot."
        plt.text(0.5, 0.5, message, ha="center", va="center", fontsize=12, color="k")
        plt.axis("off")
        return dotplot

    sc.tl.rank_genes_groups(
        adata=adata,
        groupby=leiden_res,
        groups=clusters_with_enough_cells,
        method="t-test",
    )
    data = pd.DataFrame.from_records(adata.uns["rank_genes_groups"]["names"])
    top_genes = []
    for cluster_idx in range(len(data.columns)):
        for rank_idx in range(3):
            item = data.iloc[rank_idx, cluster_idx]
            if item not in top_genes:
                top_genes.append(item)
    adata.var_names = [x for x in adata.var.index.to_list()]

    idx = max(0, min(23, len(data.columns) - 8))
    figsize_x = np.linspace(8, 20, num=24)[idx]
    figsize_y = np.linspace(4, 8, num=24)[idx]
    dotplot = sc.pl.dotplot(
        adata,
        var_names=top_genes,
        groupby=leiden_res,
        dendrogram=False,
        standard_scale="var",
        cmap=cmap,
        figsize=(figsize_x, figsize_y),
        return_fig=True,
    )

    return dotplot


def make_empty_anndata(num_entries: int = 1) -> anndata._core.anndata.AnnData:
    adata = anndata.AnnData(
        obs=pd.DataFrame(
            {
                "volume": num_entries * [0.0],
                "center_x": num_entries * [0.0],
                "center_y": num_entries * [0.0],
                "leiden_1.0": num_entries * ["0"],
            }
        ),
        obsm={"X_umap": np.vstack(num_entries * [np.array([[0, 0]])])},
        uns={"log1p": {}, "empty_anndata_indicator": None},
    )
    adata.obs.index.name = "cell"

    return adata


@timeout(PLOT_RENDERING_TIMEOUT)
def make_plot_with_timeout(plot, plot_name: str) -> None:
    plot.write_image(plot_name, format="png", engine="kaleido")


def plot_to_base64(plot) -> str:
    with tempfile.TemporaryDirectory() as temp_dir:
        plot_name = os.path.join(temp_dir, "plot.png")
        try:
            if isinstance(plot, go.Figure):
                make_plot_with_timeout(plot, plot_name)
            else:
                plot.savefig(plot_name, dpi=75, pad_inches=0.25, facecolor="white")

        except Exception:
            # If rendering failed for any reason, including a timeout error, make a placeholder figure
            plot = plt.figure(figsize=(5, 5))
            message = "Plot rendering error."
            plt.text(0.5, 0.5, message, ha="center", va="center", fontsize=18, color="#E02873")
            plt.axis("off")
            plot.savefig(plot_name, dpi=50, pad_inches=0.0, facecolor="white")

        with open(plot_name, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")

    return f"data:image/png;base64,{image_data}"


def compute_range(x):
    min_, max_ = x.min(), x.max()
    return min_ - (max_ - min_) * 0.05, max_ + (max_ - min_) * 0.05
