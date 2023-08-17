import argparse
import warnings

import pandas as pd
from vpt_core import log
from vpt_core.io.output_tools import make_parent_dirs
from vpt_core.io.vzgfs import vzg_open, retrying_attempts, io_with_retries

from vpt.partition_transcripts.cell_x_gene import cell_by_gene_matrix
from vpt.partition_transcripts.cmd_args import validate_args, PartitionTranscriptsArgs
from vpt.utils.boundaries import Boundaries
from vpt.utils.cellsreader import CellsReader, cell_reader_factory


def main_partition_transcripts(args: argparse.Namespace) -> None:
    # Suppress parquet / Arrow warnings
    warnings.filterwarnings("ignore", category=UserWarning)

    validate_args(PartitionTranscriptsArgs(**vars(args)))
    log.info("Partition transcripts started")

    cellsReader: CellsReader = cell_reader_factory(args.input_boundaries)
    bnds = Boundaries(cellsReader)

    for attempt in retrying_attempts():
        with attempt, vzg_open(args.input_transcripts, "r") as f:
            chunks = pd.read_csv(f, chunksize=args.chunk_size)
            if args.output_transcripts:
                make_parent_dirs(args.output_transcripts)

            cell_x_gene = cell_by_gene_matrix(bnds, chunks, args.output_transcripts)

    make_parent_dirs(args.output_entity_by_gene)
    io_with_retries(args.output_entity_by_gene, "w", cell_x_gene.to_csv)
    log.info(f"cell by gene matrix saved as {args.output_entity_by_gene}")

    if args.output_transcripts:
        log.info(f"detected transcripts saved as {args.output_transcripts}")

    log.info("Partition transcripts finished")
