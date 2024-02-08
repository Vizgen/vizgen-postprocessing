import random
from typing import Any, Dict, List

import numpy as np
import plotly.express as px
import plotly.graph_objs as go
from vpt.generate_segmentation_metrics.distributions_utils import (
    convert_args,
    crop_segmentation,
    make_dotplot,
    plot_to_base64,
)
from vpt.generate_segmentation_metrics.metrics_settings import FACTOR, SIZE_X, SIZE_Y
from vpt.utils.process_patch import process_patch


class Distributions:
    def __init__(self, distribution_inputs: Dict) -> None:
        self.extract_args = distribution_inputs["extract_args"]
        self.cell_by_gene = distribution_inputs["cell_by_gene"]
        self.cell_by_gene_filtered = distribution_inputs["cell_by_gene_filtered"]
        self.cell_metadata = distribution_inputs["cell_metadata"]
        self.cell_metadata_filtered = distribution_inputs["cell_metadata_filtered"]
        self.adata = distribution_inputs["cluster_ann"]
        self.detected_transcripts = distribution_inputs["detected_transcripts"]
        self.gdf = distribution_inputs["cell_polys"]
        self.image_reader = distribution_inputs.get("image_reader")

        self.distributions: Dict[str, Any] = {}
        self.preview_locations: List[List] = []

        self.marker_size = 1.0
        if self.cell_by_gene.shape[0] > 5e5:
            self.marker_size = 0.05
        if self.cell_by_gene.shape[0] < 1e5:
            self.marker_size = round(np.linspace(3, 1, num=int(1e5))[self.cell_by_gene.shape[0]], 2)

        self.font = "Gill Sans, sans-serif"
        self.leiden_res = [item for item in self.adata.obs.columns if item.startswith("leiden")][0]

        data_range_x = self.cell_metadata["center_x"].max() - self.cell_metadata["center_x"].min()
        data_range_y = self.cell_metadata["center_y"].max() - self.cell_metadata["center_y"].min()

        if data_range_x > data_range_y:
            self.x_factor = data_range_x / data_range_y
            self.y_factor = 1
        else:
            self.x_factor = 1
            self.y_factor = data_range_y / data_range_x

    def make_distributions(self) -> Dict:
        _ = self.make_seg_previews()
        _ = self.make_seg_preview_locs()
        _ = self.make_cc_cv()
        _ = self.make_cc_cluster()
        _ = self.make_cc_tpc()
        _ = self.make_cc_unique_tpc()
        _ = self.make_umap_cv()
        _ = self.make_umap_cluster()
        _ = self.make_umap_tpc()
        _ = self.make_umap_unique_tpc()
        _ = self.make_cv_hist()
        _ = self.make_tpc_hist()
        _ = self.make_tpc_cv()
        _ = self.make_unique_tpc_hist()
        _ = self.make_dotplot_fig()
        _ = self.make_top_20_genes()
        _ = self.make_bottom_20_genes()

        return self.distributions

    def make_seg_previews(self):
        seg_figs = []
        retries = 100
        for n in range(3):
            for r in range(retries):
                size_x = min(SIZE_X, self.cell_metadata["center_x"].max() - self.cell_metadata["center_x"].min() - 1e-5)
                size_y = min(SIZE_Y, self.cell_metadata["center_y"].max() - self.cell_metadata["center_y"].min() - 1e-5)

                center_x = random.uniform(
                    self.cell_metadata["center_x"].min() + 0.5 * size_x,
                    self.cell_metadata["center_x"].max() - 0.5 * size_x,
                )
                center_y = random.uniform(
                    self.cell_metadata["center_y"].min() + 0.5 * size_y,
                    self.cell_metadata["center_y"].max() - 0.5 * size_y,
                )
                extract_args_converted = convert_args(self.extract_args, center_x, center_y, size_x, size_y)
                patch_args = [self.image_reader] if self.image_reader is not None else []
                try:
                    seg_image = process_patch(extract_args_converted, *patch_args)
                except ValueError:
                    continue
                seg_polys = crop_segmentation(extract_args_converted, self.gdf)

                tpc_sample = self.cell_by_gene_filtered.loc[
                    self.cell_by_gene_filtered.index.isin(seg_polys["EntityID"].unique())
                ].sum(axis=1)
                if len(tpc_sample) > 0:
                    self.preview_locations.append([center_x, center_y, size_x, size_y])
                    break
                if r == retries - 1:
                    self.preview_locations.append([center_x, center_y, size_x, size_y])

            fig = go.Figure(px.imshow(seg_image, binary_compression_level=9))

            scatter_traces = []
            for z, df in seg_polys.groupby("ZIndex"):
                if z != self.extract_args.input_z_index:
                    continue
                for _, row in df.iterrows():
                    shape = row["Geometry"]
                    for geom in shape.geoms:
                        x = list(geom.exterior.xy[0])
                        y = list(geom.exterior.xy[1])
                        scatter_trace = go.Scatter(
                            x=x,
                            y=y,
                            mode="lines",
                            line=dict(color="white", width=1),
                            name=row["EntityID"],
                            legendgroup="cells",
                            showlegend=False,
                        )
                        scatter_traces.append(scatter_trace)

            fig.add_traces(scatter_traces)
            fig.add_trace(
                go.Scatter(
                    x=[None],
                    y=[None],
                    mode="markers",
                    marker=dict(size=0),
                    showlegend=True,
                    name="Toggle on/off cells",
                    legendgroup="cells",
                )
            )
            fig.update_layout(
                width=296,
                height=347,
                margin={"l": 2, "r": 2, "t": 20, "b": 20},
                font={"family": f"{self.font}", "size": 10},
                legend=dict(x=0.2, y=-0.15),
            )
            fig.update_xaxes(range=[0, int(FACTOR * SIZE_X)], tickvals=[], ticktext=[], showgrid=False)
            fig.update_yaxes(range=[0, int(FACTOR * SIZE_Y)], tickvals=[], ticktext=[], showgrid=False)

            seg_figs.append(fig)
            self.distributions[f"plot_div{n+1}"] = fig
            self.distributions[
                f"plot_header{n+1}"
            ] = f"Segmentation Preview {n+1}:<br>Center=({center_x:.2f}, {center_y:.2f})"
        return seg_figs

    def make_seg_preview_locs(self):
        num_spatial_bins = [512, 512]
        h, xedges, yedges = np.histogram2d(
            self.detected_transcripts["global_y"],
            self.detected_transcripts["global_x"],
            bins=num_spatial_bins,
        )
        factor = 100 / ((xedges[1] - xedges[0]) * (yedges[1] - yedges[0]))
        tissue = px.imshow(
            img=factor * h,
            x=yedges[:-1],
            y=xedges[:-1],
            color_continuous_scale=px.colors.sequential.Blues,
            binary_compression_level=9,
            template="simple_white",
        )
        for i, preview in enumerate(self.preview_locations):
            tissue.add_shape(
                type="rect",
                x0=preview[0] - 0.5 * preview[2],
                x1=preview[0] + 0.5 * preview[2],
                y0=preview[1] - 0.5 * preview[3],
                y1=preview[1] + 0.5 * preview[3],
                line=dict(color="red", width=3),
                fillcolor="rgba(0,0,0,0)",
            )
            tissue.add_annotation(
                x=preview[0],
                y=preview[1] - 0.5 * preview[2] - 50,
                text=str(i + 1),
                font=dict(size=12, color="red"),
                showarrow=False,
            )
        tissue.update_layout(
            width=296,
            height=347,
            margin={"l": 8, "r": 8, "t": 25, "b": 20},
            font={"family": f"{self.font}", "size": 10},
            xaxis=dict(showticklabels=False, showline=False, ticks="", showgrid=False),
            yaxis=dict(showticklabels=False, showline=False, ticks="", showgrid=False),
            coloraxis_showscale=False,
        )
        self.distributions["plot_div0"] = tissue
        self.distributions["plot_header0"] = "Segmentation Preview Locations"
        return tissue

    def make_cv_hist(self):
        cv = go.Figure()
        cv_trace = go.Histogram(
            x=self.cell_metadata["volume"] + 1, marker=dict(color="#1f77b4"), name="All cells", nbinsx=100
        )
        cv.add_trace(cv_trace)
        cv.update_xaxes(title_text="Volume (\u00b5m<sup>3</sup>)")
        cv.update_yaxes(title_text="Count")  # , type="log", dtick=1)
        cv.update_layout(
            width=296,
            height=342,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            font={"family": f"{self.font}", "size": 10},
            legend=dict(x=0.1, y=-0.2, orientation="h", yanchor="top"),
            barmode="overlay",
            plot_bgcolor="white",
            yaxis=dict(gridcolor="black"),
        )
        cv.add_shape(
            type="line",
            x0=self.extract_args.volume_filter_threshold,
            x1=self.extract_args.volume_filter_threshold,
            y0=0,
            y1=0.02 * self.cell_by_gene.shape[0],
            line=dict(color="gray", width=2, dash="dash"),
        )
        cv.add_annotation(
            x=np.log10(self.extract_args.volume_filter_threshold),
            y=0.02 * self.cell_by_gene.shape[0],
            text="volume_filter_threshold",
            font=dict(size=12, color="black"),
            xanchor="left",
            yanchor="bottom",
            showarrow=False,
        )
        trace2 = go.Histogram(
            x=self.cell_metadata_filtered["volume"] + 1, marker=dict(color="#ff7f0e"), name="Filtered cells", nbinsx=100
        )
        cv.add_trace(trace2)
        self.distributions["plot_div4"] = cv
        self.distributions["plot_header4"] = "Cell Volume"
        return cv

    def make_tpc_hist(self):
        tpc = go.Figure()
        trace = go.Histogram(
            x=self.cell_by_gene.sum(axis=1), marker=dict(color="#1f77b4"), name="All cells", nbinsx=100
        )
        tpc.add_trace(trace)
        tpc.update_xaxes(title_text="Transcripts per cell")
        tpc.update_yaxes(title_text="Count", type="log", dtick=1)
        tpc.update_layout(
            width=296,
            height=342,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            font={"family": f"{self.font}", "size": 10},
            legend=dict(x=0.1, y=-0.2, orientation="h", yanchor="top"),
            barmode="overlay",
            plot_bgcolor="white",
            yaxis=dict(gridcolor="black"),
        )
        tpc.add_shape(
            type="line",
            x0=self.extract_args.transcript_count_filter_threshold,
            x1=self.extract_args.transcript_count_filter_threshold,
            y0=1,
            y1=0.015 * self.cell_by_gene.shape[0],
            line=dict(color="gray", width=2, dash="dash"),
        )
        tpc.add_annotation(
            x=self.extract_args.transcript_count_filter_threshold,
            y=np.log10(0.015 * self.cell_by_gene.shape[0]),
            text="transcript_count_filter_threshold",
            font=dict(size=12, color="black"),
            xanchor="left",
            yanchor="bottom",
            showarrow=False,
        )
        trace2 = go.Histogram(
            x=self.cell_by_gene_filtered.sum(axis=1) + 1,
            marker=dict(color="#ff7f0e"),
            name="Filtered cells",
            nbinsx=100,
        )
        tpc.add_trace(trace2)
        self.distributions["plot_div5"] = tpc
        self.distributions["plot_header5"] = "Transcripts per Cell"
        return tpc

    def make_unique_tpc_hist(self):
        unique_tpc = go.Figure()
        trace = go.Histogram(
            x=np.count_nonzero(self.cell_by_gene, axis=1), marker=dict(color="#1f77b4"), name="All cells", nbinsx=100
        )
        unique_tpc.add_trace(trace)
        unique_tpc.update_xaxes(title_text="Unique genes per cell")
        unique_tpc.update_yaxes(title_text="Count", type="log", dtick=1)
        unique_tpc.update_layout(
            width=296,
            height=342,
            showlegend=True,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            font={"family": f"{self.font}", "size": 10},
            legend=dict(x=0.1, y=-0.2, orientation="h", yanchor="top"),
            barmode="overlay",
            plot_bgcolor="white",
            yaxis=dict(gridcolor="black"),
        )
        trace2 = go.Histogram(
            x=np.count_nonzero(self.cell_by_gene_filtered, axis=1),
            marker=dict(color="#ff7f0e"),
            name="Filtered cells",
            nbinsx=100,
        )
        unique_tpc.add_trace(trace2)
        self.distributions["plot_div6"] = unique_tpc
        self.distributions["plot_header6"] = "Unique Genes per Cell"
        return unique_tpc

    def make_tpc_cv(self):
        tpc_cv = go.Figure()
        tpc_cv_trace = go.Scatter(
            x=self.cell_metadata["volume"],
            y=self.cell_by_gene.sum(axis=1),
            mode="markers",
            marker=dict(size=self.marker_size, color="#1f77b4"),
            name="All cells",
        )
        tpc_cv.add_trace(tpc_cv_trace)

        tpc_cv.update_xaxes(title_text="Cell volume (\u00b5m<sup>3</sup>)")
        tpc_cv.update_yaxes(title_text="Transcripts per cell")
        tpc_cv.update_layout(
            width=296,
            height=342,
            showlegend=False,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            font={"family": f"{self.font}", "size": 10},
            plot_bgcolor="white",
            yaxis=dict(gridcolor="black"),
        )
        self.distributions["plot_div7"] = plot_to_base64(tpc_cv)
        self.distributions["plot_header7"] = "Transcripts per Cell vs. Cell Volume"
        return tpc_cv

    def make_cc_cv(self):
        cc_cv_trace = go.Scattergl(
            x=self.cell_metadata["center_x"],
            y=self.cell_metadata["center_y"],
            mode="markers",
            marker=dict(
                size=self.marker_size,
                color=np.log10(self.cell_metadata["volume"] + 1),
                colorscale="Viridis",
                colorbar=dict(
                    title="Cell volume (log<sub>10</sub> \u00b5m<sup>3</sup>)",
                    title_side="right",
                    len=1.0,
                    thickness=15,
                ),
            ),
        )
        layout = go.Layout(
            xaxis=dict(title_text="X (\u00b5m)"),
            yaxis=dict(title_text="Y (\u00b5m)", autorange="reversed"),
            width=296,
            height=258,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            font={"family": f"{self.font}", "size": 10},
        )
        cc_cv = go.Figure(data=[cc_cv_trace], layout=layout)
        self.distributions["plot_div8"] = plot_to_base64(cc_cv)
        self.distributions["plot_header8"] = "Cell Centers Colored by Cell Volume"
        return cc_cv

    def make_cc_tpc(self):
        cc_tpc_trace = go.Scattergl(
            x=self.cell_metadata["center_x"],
            y=self.cell_metadata["center_y"],
            mode="markers",
            marker=dict(
                size=self.marker_size,
                color=np.log10(self.cell_by_gene.sum(axis=1).to_numpy() + 1),
                colorscale="Viridis",
                colorbar=dict(title="Transcript count (log<sub>10</sub>)", title_side="right", len=1.0, thickness=15),
            ),
        )
        layout = go.Layout(
            xaxis=dict(title_text="X (\u00b5m)"),
            yaxis=dict(title_text="Y (\u00b5m)", autorange="reversed"),
            width=296,
            height=258,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            font={"family": f"{self.font}", "size": 10},
        )
        cc_tpc = go.Figure(data=[cc_tpc_trace], layout=layout)
        self.distributions["plot_div9"] = plot_to_base64(cc_tpc)
        self.distributions["plot_header9"] = "Cell Centers Colored by Transcript Count"
        return cc_tpc

    def make_cc_unique_tpc(self):
        cc_unique_tpc_trace = go.Scattergl(
            x=self.cell_metadata["center_x"],
            y=self.cell_metadata["center_y"],
            mode="markers",
            marker=dict(
                size=self.marker_size,
                color=np.log10(np.count_nonzero(self.cell_by_gene, axis=1) + 1),
                colorscale="Viridis",
                colorbar=dict(title="Unique genes count (log<sub>10</sub>)", title_side="right", len=1.0, thickness=15),
            ),
        )
        layout = go.Layout(
            xaxis=dict(title_text="X (\u00b5m)"),
            yaxis=dict(title_text="Y (\u00b5m)", autorange="reversed"),
            width=296,
            height=258,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            font={"family": f"{self.font}", "size": 10},
        )
        cc_unique_tpc = go.Figure(data=[cc_unique_tpc_trace], layout=layout)
        self.distributions["plot_div10"] = plot_to_base64(cc_unique_tpc)
        self.distributions["plot_header10"] = "Cell Centers Colored by Unique Gene Count"
        return cc_unique_tpc

    def make_cc_cluster(self):
        cc_cluster = px.scatter(
            x=self.adata.obs["center_x"],
            y=self.adata.obs["center_y"],
            color=self.adata.obs[self.leiden_res],
            render_mode="webgl",
        )
        cc_cluster.update_traces(marker_size=self.marker_size)
        cc_cluster.update_coloraxes(colorbar_title="Cluster")
        cc_cluster.update_layout(
            xaxis_title_text="X (\u00b5m)",
            yaxis_title_text="Y (\u00b5m)",
            width=296,
            height=258,
            yaxis=dict(autorange="reversed"),
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            font={"family": f"{self.font}", "size": 10},
            legend=dict(
                title=dict(text="Cell<br>cluster", side="top"),
                orientation="v",
            ),
        )
        self.distributions["plot_div11"] = cc_cluster
        self.distributions["plot_header11"] = "Cell Centers Colored by Cell Cluster"
        return cc_cluster

    def make_umap_cv(self):
        umap1 = px.scatter(
            x=self.adata.obsm["X_umap"][:, 0],
            y=self.adata.obsm["X_umap"][:, 1],
            color=np.log10(self.adata.obs["volume"] + 1),
            color_continuous_scale="Viridis",
            render_mode="webgl",
        )
        umap1.update_traces(marker_size=self.marker_size)
        umap1.update_xaxes(title_text="", tickvals=[], ticktext=[], showgrid=False)
        umap1.update_yaxes(title_text="", tickvals=[], ticktext=[], showgrid=False)
        umap1.update_coloraxes(colorbar_title="Cell volume (log<sub>10</sub> \u00b5m<sup>3</sup>)")
        umap1.update_layout(
            width=296,
            height=272,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            font={"family": f"{self.font}", "size": 10},
            coloraxis_colorbar=dict(title_side="right", len=1.0, thickness=15),
        )
        self.distributions["plot_div12"] = plot_to_base64(umap1)
        self.distributions["plot_header12"] = "UMAP Colored by Cell Volume"
        return umap1

    def make_umap_tpc(self):
        umap2 = px.scatter(
            x=self.adata.obsm["X_umap"][:, 0],
            y=self.adata.obsm["X_umap"][:, 1],
            color=np.log10(self.cell_by_gene_filtered.sum(axis=1).to_numpy()),
            color_continuous_scale="Viridis",
            render_mode="webgl",
        )
        umap2.update_traces(marker_size=self.marker_size)
        umap2.update_xaxes(title_text="", tickvals=[], ticktext=[], showgrid=False)
        umap2.update_yaxes(title_text="", tickvals=[], ticktext=[], showgrid=False)
        umap2.update_coloraxes(colorbar_title="Transcript count (log<sub>10</sub>)")
        umap2.update_layout(
            width=296,
            height=272,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            font={"family": f"{self.font}", "size": 10},
            coloraxis_colorbar=dict(title_side="right", len=1.0, thickness=15),
        )
        self.distributions["plot_div13"] = plot_to_base64(umap2)
        self.distributions["plot_header13"] = "UMAP Colored by Transcript Count"
        return umap2

    def make_umap_unique_tpc(self):
        umap3 = px.scatter(
            x=self.adata.obsm["X_umap"][:, 0],
            y=self.adata.obsm["X_umap"][:, 1],
            color=np.log10(np.count_nonzero(self.cell_by_gene_filtered, axis=1) + 1),
            color_continuous_scale="Viridis",
        )
        umap3.update_traces(marker_size=self.marker_size)
        umap3.update_xaxes(title_text="", tickvals=[], ticktext=[], showgrid=False)
        umap3.update_yaxes(title_text="", tickvals=[], ticktext=[], showgrid=False)
        umap3.update_coloraxes(colorbar_title="Unique gene count (log<sub>10</sub>)")
        umap3.update_layout(
            width=296,
            height=272,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            font={"family": f"{self.font}", "size": 10},
            coloraxis_colorbar=dict(title_side="right", len=1.0, thickness=15),
        )
        self.distributions["plot_div14"] = plot_to_base64(umap3)
        self.distributions["plot_header14"] = "UMAP Colored by Unique Gene Count"
        return umap3

    def make_umap_cluster(self):
        umap4 = px.scatter(
            x=self.adata.obsm["X_umap"][:, 0],
            y=self.adata.obsm["X_umap"][:, 1],
            color=self.adata.obs[self.leiden_res],
            render_mode="webgl",
        )
        umap4.update_traces(marker_size=self.marker_size)
        umap4.update_xaxes(title_text="", tickvals=[], ticktext=[], showgrid=False)
        umap4.update_yaxes(title_text="", tickvals=[], ticktext=[], showgrid=False)
        umap4.update_coloraxes(colorbar_title="Cluster")
        umap4.update_layout(
            width=296,
            height=272,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            font={"family": f"{self.font}", "size": 10},
            legend=dict(
                title=dict(text="Cell<br>cluster", side="top"),
                orientation="v",
            ),
        )
        self.distributions["plot_div15"] = umap4
        self.distributions["plot_header15"] = "UMAP Colored by Cell Cluster"
        return umap4

    def make_dotplot_fig(self):
        dotplot = make_dotplot(self.adata)
        self.distributions["plot_div16"] = plot_to_base64(dotplot)
        self.distributions["plot_header16"] = "Gene Expression by Cluster"
        return dotplot

    def make_top_20_genes(self):
        gene_counts = self.detected_transcripts["gene"].value_counts()
        gene_partition_all = self.cell_by_gene.sum().reindex(gene_counts.index) / gene_counts
        gene_partition_all = gene_partition_all.sort_values(ascending=False)
        top_20_genes_all = gene_partition_all.head(20)

        gene_partition = self.cell_by_gene_filtered.sum().reindex(gene_counts.index) / gene_counts
        top_20_genes_filtered = gene_partition.loc[top_20_genes_all.index]

        top_20 = go.Bar(
            x=top_20_genes_all.index, y=top_20_genes_all.values, marker=dict(color="#1f77b4"), name="All cells"
        )
        top_20_filtered = go.Bar(
            x=top_20_genes_filtered.index,
            y=top_20_genes_filtered.values,
            marker=dict(color="#ff7f0e"),
            name="Filtered cells",
        )
        layout = go.Layout(
            xaxis=dict(title_text="Gene", tickangle=45),
            yaxis=dict(
                title_text="Fraction of transcripts within a cell", tickangle=45, range=[0, 1], gridcolor="black"
            ),
            width=632,
            height=350,
            showlegend=True,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            font={"family": f"{self.font}", "size": 10},
            legend=dict(x=1, y=0.5),
            barmode="overlay",
            plot_bgcolor="white",
        )
        top_20_combined = go.Figure(data=[top_20, top_20_filtered], layout=layout)
        self.distributions["plot_div17"] = top_20_combined
        self.distributions["plot_header17"] = "Top 20 Partitioned Genes"
        return top_20_combined

    def make_bottom_20_genes(self):
        gene_counts = self.detected_transcripts["gene"].value_counts()
        gene_partition_all = self.cell_by_gene.sum().reindex(gene_counts.index) / gene_counts
        gene_partition_all = gene_partition_all.sort_values(ascending=False)
        bottom_20_genes_all = gene_partition_all.tail(20)

        gene_partition = self.cell_by_gene_filtered.sum().reindex(gene_counts.index) / gene_counts
        bottom_20_genes_filtered = gene_partition.loc[bottom_20_genes_all.index]

        bottom_20 = go.Bar(
            x=bottom_20_genes_all.index, y=bottom_20_genes_all.values, marker=dict(color="#1f77b4"), name="All cells"
        )
        bottom_20_filtered = go.Bar(
            x=bottom_20_genes_filtered.index,
            y=bottom_20_genes_filtered.values,
            marker=dict(color="#ff7f0e"),
            name="Filtered cells",
        )
        layout = go.Layout(
            xaxis=dict(title_text="Gene", tickangle=45),
            yaxis=dict(
                title_text="Fraction of transcripts within a cell", tickangle=45, range=[0, 1], gridcolor="black"
            ),
            width=632,
            height=350,
            showlegend=True,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            font={"family": f"{self.font}", "size": 10},
            legend=dict(x=1, y=0.5),
            barmode="overlay",
            plot_bgcolor="white",
        )
        bottom_20_combined = go.Figure(data=[bottom_20, bottom_20_filtered], layout=layout)
        self.distributions["plot_div18"] = bottom_20_combined
        self.distributions["plot_header18"] = "Bottom 20 Partitioned Genes"
        return bottom_20_combined
