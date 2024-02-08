from pathlib import Path
from typing import Dict

import pyarrow as pa
from vpt_core.io.vzgfs import (
    Protocol,
    filesystem_for_protocol,
    filesystem_path_split,
    io_with_retries,
    protocol_path_split,
)


def save_to_parquets(output_dfs: Dict, output_dir) -> None:
    for file_name, output_df in output_dfs.items():
        fs, path_inside_fs = filesystem_path_split(output_dir)
        fs.mkdirs(path_inside_fs, exist_ok=True)

        io_with_retries(
            uri=f"{output_dir}/{file_name}",
            mode="wb",
            callback=lambda f: pa.parquet.write_table(pa.Table.from_pandas(output_df), f, compression="gzip"),
        )


def make_parent_folder(uri: str):
    protocol, path = protocol_path_split(uri)
    if protocol == Protocol.LOCAL:
        parent_dir = str(Path(path).parent)
        fs = filesystem_for_protocol(protocol)
        fs.makedirs(parent_dir, exist_ok=True)
