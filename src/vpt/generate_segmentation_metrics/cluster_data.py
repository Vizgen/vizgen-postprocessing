import anndata
import pandas as pd
import scanpy as sc
import vpt.generate_segmentation_metrics.metrics_settings as metrics_settings


def cell_by_gene_norm(
    cell_by_gene: pd.DataFrame,
    cell_metadata: pd.DataFrame,
    min_genes_per_cell=0,
    min_count_per_cell=0,
) -> anndata._core.anndata.AnnData:
    cell_x_gene_no_blanks = cell_by_gene.loc[:, ["Blank" not in c for c in cell_by_gene.columns]]

    expr_ann = anndata.AnnData(
        X=cell_x_gene_no_blanks.to_numpy(),
        obs=cell_x_gene_no_blanks.join(cell_metadata)[["volume", "center_x", "center_y"]],
        var=pd.DataFrame(index=cell_x_gene_no_blanks.columns),
    )

    sc.pp.filter_cells(expr_ann, min_counts=min_count_per_cell)
    sc.pp.filter_cells(expr_ann, min_genes=min_genes_per_cell)
    sc.pp.normalize_total(expr_ann)
    sc.pp.log1p(expr_ann)
    sc.pp.scale(expr_ann, zero_center=False)

    return expr_ann


def cluster_expression_data(
    expr_ann,
    pca_solver="arpack",
    umap_neighbors=10,
    umap_pcs=20,
    min_dist=0.5,
    spread=1.0,
    leiden_resolution=[1.0],
) -> anndata._core.anndata.AnnData:
    sc.tl.pca(expr_ann, svd_solver=pca_solver)
    sc.pp.neighbors(expr_ann, n_neighbors=umap_neighbors, n_pcs=umap_pcs)
    sc.tl.umap(
        expr_ann,
        min_dist=min_dist,
        spread=spread,
    )

    leiden_resolution_keys = ["leiden_{}".format(r) for r in leiden_resolution]
    for r, k in zip(leiden_resolution, leiden_resolution_keys):
        sc.tl.leiden(expr_ann, resolution=r, key_added=k)

    return expr_ann


def cluster_data(
    cell_by_gene_filtered: pd.DataFrame, cell_metadata_filtered: pd.DataFrame
) -> anndata._core.anndata.AnnData:
    expr_ann = cell_by_gene_norm(
        cell_by_gene_filtered,
        cell_metadata_filtered,
        min_genes_per_cell=metrics_settings.MIN_GENES_PER_CELL,
        min_count_per_cell=metrics_settings.MIN_COUNT_PER_CELL,
    )
    cluster_ann = cluster_expression_data(
        expr_ann,
        pca_solver=metrics_settings.PCA_SOLVER,
        umap_neighbors=metrics_settings.UMAP_NEIGHBORS,
        umap_pcs=metrics_settings.UMAP_PCS,
        min_dist=metrics_settings.MIN_DIST,
        spread=metrics_settings.SPREAD,
        leiden_resolution=metrics_settings.LEIDEN_RESOLUTION,
    )

    return cluster_ann
