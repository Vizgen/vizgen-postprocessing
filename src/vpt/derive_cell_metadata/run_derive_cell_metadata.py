import argparse

import pandas as pd
import numpy as np
from vpt.filesystem.vzgfs import vzg_open
from vpt.utils.boundaries import Boundaries
from vpt.derive_cell_metadata.cell_metadata import create_metadata_table
from vpt.utils.cellsreader import CellsReader, cell_reader_factory
from vpt.utils.output_tools import make_parent_dirs
from vpt.derive_cell_metadata.cmd_args import validate_args
import vpt.log as log


def main_derive_cell_metadata(args: argparse.Namespace) -> None:
    validate_args(args)

    log.info('Derive cell metadata started')
    barcodesSumList = None
    if args.input_entity_by_gene:
        with vzg_open(args.input_entity_by_gene, 'r') as f:
            cellByGeneDf = pd.read_csv(f)
        cellByGeneNp = cellByGeneDf.to_numpy()
        barcodesSumList = [np.sum(row[1:]) for row in cellByGeneNp]

    cellsReader: CellsReader = cell_reader_factory(args.input_boundaries)
    bnds = Boundaries(cellsReader)

    meta = create_metadata_table(bnds, cellsReader.get_z_levels(), barcodesSumList)

    make_parent_dirs(args.output_metadata)
    with vzg_open(args.output_metadata, 'w') as f:
        meta.to_csv(f, sep=',')

    log.info('Derive cell metadata finished')
