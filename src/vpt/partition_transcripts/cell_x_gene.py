from typing import List, Optional

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import shapely
from shapely import Polygon
from vpt_core.io.vzgfs import get_storage_options, retrying_attempts, vzg_open

from vpt.utils.boundaries import Boundaries

ROW_GROUP_SIZE = 10_000_000  # about 1 GB in memory


def read_parquet_chunked(f, chunksize: int):
    file = pq.ParquetFile(f)

    if file.metadata.num_rows == 0:
        yield file.read().to_pandas()
        return

    for chunk in file.iter_batches(chunksize):
        temp = chunk.to_pandas()
        if "" in temp.columns:
            yield temp.rename(columns={"": "Unnamed: 0"})
        else:
            yield temp.reset_index().rename(columns={"index": "Unnamed: 0"})


def get_chunks(input_transcripts: str, chunk_size: int):
    if input_transcripts.endswith(".csv"):
        with vzg_open(input_transcripts, "r") as f:
            yield from pd.read_csv(f, chunksize=chunk_size)
    elif input_transcripts.endswith(".parquet"):
        with vzg_open(input_transcripts, "rb") as f:
            yield from read_parquet_chunked(f, chunksize=chunk_size)
    else:
        raise NotImplementedError()


def write_detected_transcripts(transcripts_df: pd.DataFrame, output_path: str, append: bool = False) -> None:
    storage_options = get_storage_options(output_path)

    for attempt in retrying_attempts():
        with attempt:
            if output_path.endswith(".csv"):
                transcripts_df.to_csv(
                    output_path,
                    index=False,
                    header=not append,
                    mode="a" if append else "w",
                    storage_options=storage_options,
                )
            elif output_path.endswith(".parquet"):
                transcripts_df.to_parquet(
                    output_path,
                    engine="fastparquet",
                    index=False,
                    append=append,
                    compression="zstd",
                    row_group_offsets=ROW_GROUP_SIZE,
                    storage_options=storage_options,
                )
            else:
                raise NotImplementedError()


def process_chunk(chunk_df, shapely_list, z_planes_count, cell_id_list, needs_new_dt: bool = False):
    genes_detected = chunk_df["gene"].unique()
    grouped = chunk_df.groupby(chunk_df["gene"])

    gene_df_list = []
    transcripts_list = []
    for gene in genes_detected:
        one_gene = grouped.get_group(gene)
        one_gene_partition_list = []
        for z in range(z_planes_count):
            one_gene_z = one_gene.loc[one_gene["global_z"] == z]
            points = shapely.points(one_gene_z["global_x"], one_gene_z["global_y"])
            one_gene_tree = shapely.STRtree(points)
            one_gene_partition_z = one_gene_tree.query(shapely_list[z], predicate="contains")
            one_gene_partition_list.append(one_gene_partition_z)

            if needs_new_dt:
                out = np.full(len(one_gene_z), -1, dtype=np.int64)
                if len(one_gene_partition_z[0]) > 0:
                    cell_id_vectorize = np.vectorize(lambda t: cell_id_list[t])
                    out[one_gene_partition_z[1]] = cell_id_vectorize(one_gene_partition_z[0])

                one_gene_z = one_gene_z.assign(cell_id=out)

                transcripts_list.append(one_gene_z)

        if needs_new_dt:
            unhandled_transcripts = one_gene.loc[(one_gene["global_z"] >= z_planes_count) | (one_gene["global_z"] < 0)]
            unhandled_transcripts.assign(cell_id=-1)
            if len(unhandled_transcripts) > 0:
                transcripts_list.append(unhandled_transcripts)

        if one_gene_partition_list:
            one_gene_partition = np.concatenate(one_gene_partition_list, axis=1)
        else:
            one_gene_partition = np.array([[], []])

        cell_x_one_gene = pd.DataFrame(one_gene_partition.T, columns=["cell_id", gene]).groupby("cell_id").count()
        gene_df_list.append(cell_x_one_gene)

    cell_x_gene = pd.DataFrame(index=range(len(cell_id_list))).join(gene_df_list).fillna(0)
    cell_x_gene["cell"] = pd.to_numeric(cell_id_list)

    if len(transcripts_list) > 0:
        transcripts_df = pd.concat(transcripts_list).loc[chunk_df.index]
    else:
        transcripts_df = pd.DataFrame(columns=list(chunk_df.columns) + ["cell_id"])

    return cell_x_gene, transcripts_df


def construct_cell_x_gene(
    transcripts, geometry_list, z_planes_count: int, cell_id_list, output_transcripts: Optional[str] = None
) -> pd.DataFrame:
    cell_by_gene = pd.DataFrame({"cell": pd.to_numeric(cell_id_list)})
    barcode_id_name_df = pd.DataFrame(columns=["barcode_id", "gene"])

    first_chunk = True
    for chunk_df in transcripts:
        chunk_cell_by_gene, transcripts_df = process_chunk(
            chunk_df, geometry_list, z_planes_count, cell_id_list, output_transcripts is not None
        )

        cell_by_gene = (
            pd.concat([cell_by_gene, chunk_cell_by_gene]).groupby("cell").sum(min_count=1).fillna(0).reset_index()
        )

        barcode_id_name_df = pd.concat([barcode_id_name_df, chunk_df[["barcode_id", "gene"]]]).drop_duplicates(
            subset="barcode_id"
        )

        if output_transcripts is None:
            continue

        transcripts_df = transcripts_df.rename(columns={transcripts_df.columns[0]: ""})

        if first_chunk:
            write_detected_transcripts(transcripts_df, output_transcripts, append=False)
            first_chunk = False
            continue

        write_detected_transcripts(transcripts_df, output_transcripts, append=True)

    cell_by_gene.set_index("cell", inplace=True, drop=True)
    cell_by_gene.index = cell_by_gene.index.astype(np.int64)
    cell_by_gene.index.name = "cell"
    cell_by_gene = cell_by_gene.sort_index()

    barcode_id_name_df = barcode_id_name_df.set_index("barcode_id")
    barcode_id_name_df.sort_index(inplace=True)
    cell_by_gene = cell_by_gene.reindex(list(barcode_id_name_df["gene"]), axis=1)
    return cell_by_gene.astype("int")


def cell_by_gene_matrix(
    bnds: Boundaries, transcripts: pd.DataFrame, output_transcripts: Optional[str] = None
) -> pd.DataFrame:
    idList = []
    geomList: List[List[Polygon]] = []
    for z in range(bnds.get_z_planes_count()):
        geomList.append([])
    for feature in bnds.features:
        idList.append(np.int64(feature.get_feature_id()))
        for zIdx, poly in enumerate(feature.get_full_cell()):
            geomList[zIdx].append(poly)

    cell_x_gene = construct_cell_x_gene(
        transcripts, np.array(geomList), bnds.get_z_planes_count(), idList, output_transcripts
    )

    return cell_x_gene
