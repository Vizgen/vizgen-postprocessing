import argparse

import numpy as np
import pandas as pd
from vpt_core import log
from vpt_core.io.output_tools import make_parent_dirs
from vpt_core.io.vzgfs import io_with_retries

from vpt.derive_cell_metadata.cell_metadata import create_metadata_table
from vpt.derive_cell_metadata.cmd_args import validate_args, DeriveMetadataArgs
from vpt.utils.boundaries import Boundaries
from vpt.utils.cellsreader import CellsReader, cell_reader_factory


def main_derive_cell_metadata(args: argparse.Namespace) -> None:
    validate_args(DeriveMetadataArgs(**vars(args)))

    log.info("Derive cell metadata started")
    barcodesSumList = None
    if args.input_entity_by_gene:
        cellByGeneDf = io_with_retries(args.input_entity_by_gene, "r", pd.read_csv)
        cellByGeneNp = cellByGeneDf.to_numpy()
        barcodesSumList = np.array([np.sum(row[1:]) for row in cellByGeneNp])

    cellsReader: CellsReader = cell_reader_factory(args.input_boundaries)
    bnds = Boundaries(cellsReader)

    meta = create_metadata_table(bnds, cellsReader.get_z_depth_per_level(), barcodesSumList)

    make_parent_dirs(args.output_metadata)
    io_with_retries(args.output_metadata, "w", lambda f: meta.to_csv(f, sep=","))

    log.info("Derive cell metadata finished")
