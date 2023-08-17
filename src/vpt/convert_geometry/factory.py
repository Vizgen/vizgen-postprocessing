from enum import Enum
from typing import Dict, Tuple, Callable

from vpt_core.io.vzgfs import filesystem_path_split
from vpt_core.segmentation.seg_result import SegmentationResult

from vpt.convert_geometry.converters.hdf5_converter import read_segmentation_result as hdf5_reader
from vpt.convert_geometry.converters.old_parquet_converter import read_segmentation_result as parquet_reader
from vpt.convert_geometry.converters.qpath_geojson_converter import read_segmentation_result as qpath_reader


class SegmentationFileType(Enum):
    HDF5 = 0
    QPATH = 1
    PARQUET = 2
    OTHER = 3


def get_conversion_type(input_path: str) -> SegmentationFileType:
    fs, path = filesystem_path_split(input_path)
    ext = path.split(fs.sep)[-1].split(".")[-1]
    if ext == "hdf5":
        return SegmentationFileType.HDF5
    if ext == "geojson":
        return SegmentationFileType.QPATH
    if ext == "parquet":
        return SegmentationFileType.PARQUET
    return SegmentationFileType.OTHER


def read_segmentation_result(input_path: str, **kwargs) -> Tuple[SegmentationResult, Dict]:
    converters: Dict[SegmentationFileType, Callable] = {
        SegmentationFileType.HDF5: hdf5_reader,
        SegmentationFileType.QPATH: qpath_reader,
        SegmentationFileType.PARQUET: parquet_reader,
    }
    file_type = get_conversion_type(input_path)
    if file_type == SegmentationFileType.OTHER:
        raise ValueError("input file type is not supported")
    return converters[file_type](input_path, **kwargs)
