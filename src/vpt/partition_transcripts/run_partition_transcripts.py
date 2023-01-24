import argparse
import warnings
import pandas as pd

from vpt.filesystem import vzg_open
from vpt.partition_transcripts.cell_x_gene import cell_by_gene_matrix
from vpt.partition_transcripts.cmd_args import validate_args
from vpt.utils.boundaries import Boundaries
from vpt.utils.cellsreader import CellsReader, cell_reader_factory
from vpt.utils.output_tools import make_parent_dirs
import vpt.log as log


def main_partition_transcripts(args: argparse.Namespace) -> None:
    # Suppress parquet / Arrow warnings
    warnings.filterwarnings('ignore', category=UserWarning)

    validate_args(args)
    log.info('Partition transcripts started')

    cellsReader: CellsReader = cell_reader_factory(args.input_boundaries)
    bnds = Boundaries(cellsReader)

    with vzg_open(args.input_transcripts, 'r') as f:
        chunks = pd.read_csv(f, chunksize=args.chunk_size)
        if args.output_transcripts:
            make_parent_dirs(args.output_transcripts)

        cell_x_gene = cell_by_gene_matrix(bnds, chunks, args.output_transcripts)

    make_parent_dirs(args.output_entity_by_gene)
    with vzg_open(args.output_entity_by_gene, "w") as f:
        cell_x_gene.to_csv(f)
    log.info(f'cell by gene matrix saved as {args.output_entity_by_gene}')

    if args.output_transcripts:
        log.info(f'detected transcripts saved as {args.output_transcripts}')

    log.info('Partition transcripts finished')
