from vpt.derive_cell_metadata.cmd_args import parse_args
from vpt.derive_cell_metadata.run_derive_cell_metadata import main_derive_cell_metadata

if __name__ == '__main__':
    main_derive_cell_metadata(parse_args())
