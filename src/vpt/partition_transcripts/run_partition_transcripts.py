import argparse
import warnings

from vpt_core import log
from vpt_core.io.output_tools import make_parent_dirs
from vpt_core.io.vzgfs import io_with_retries, retrying_attempts

from vpt.partition_transcripts.cell_x_gene import cell_by_gene_matrix, get_chunks
from vpt.partition_transcripts.cmd_args import PartitionTranscriptsArgs, validate_args
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
        with attempt:
            chunks = get_chunks(args.input_transcripts, args.chunk_size)
            if args.output_transcripts:
                make_parent_dirs(args.output_transcripts)

            cell_x_gene = cell_by_gene_matrix(bnds, chunks, args.output_transcripts)

    make_parent_dirs(args.output_entity_by_gene)
    io_with_retries(args.output_entity_by_gene, "w", cell_x_gene.to_csv)
    log.info(f"cell by gene matrix saved as {args.output_entity_by_gene}")

    if args.output_transcripts:
        log.info(f"detected transcripts saved as {args.output_transcripts}")

    log.info("Partition transcripts finished")
