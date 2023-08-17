from vpt.utils.cellsreader.base_reader import CellsReader


def cell_reader_factory(pathToFile) -> CellsReader:
    from vpt.utils.cellsreader.geo_reader import CellsGeoReader
    from vpt.utils.cellsreader.parquet_reader import CellsParquetReader

    if pathToFile.endswith(".parquet"):
        return CellsParquetReader(pathToFile)

    elif pathToFile.endswith(".geojson"):
        return CellsGeoReader(pathToFile)

    else:
        raise ValueError("Input geometry has an unsupported file extension")
