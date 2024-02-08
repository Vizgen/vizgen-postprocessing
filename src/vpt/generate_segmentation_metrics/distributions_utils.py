import base64
import os
import tempfile
import warnings
from argparse import Namespace

import anndata
import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import scanpy as sc
import shapely
from shapely import geometry
from vpt.generate_segmentation_metrics.cmd_args import GenerateSegMetricsArgs
from vpt.utils.input_utils import read_micron_to_mosaic_transform
from vpt.utils.process_patch import ExtractImageArgs, transform_coords
from vpt_core.io.regex_tools import parse_images_str

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


def make_dotplot(adata: anndata._core.anndata.AnnData) -> sc.plotting._dotplot.DotPlot:
    leiden_res = [item for item in adata.obs.columns if item.startswith("leiden")][0]
    sc.tl.rank_genes_groups(adata=adata, groupby=leiden_res, method="t-test")
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
        cmap="Blues",
        figsize=(figsize_x, figsize_y),
        return_fig=True,
    )

    return dotplot


def plot_to_base64(plot) -> str:
    with tempfile.TemporaryDirectory() as temp_dir:
        if isinstance(plot, go.Figure):
            plot.write_image(os.path.join(temp_dir, "plot.png"), format="png", engine="kaleido")
        else:
            plot.savefig(
                os.path.join(temp_dir, "plot.png"),
                dpi=75,
                pad_inches=0.25,
                facecolor="white",
            )
        with open(os.path.join(temp_dir, "plot.png"), "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")

    return f"data:image/png;base64,{image_data}"
