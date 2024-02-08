from pathlib import Path

TEMPLATE_ROOT = (Path(__file__).parent.parent / "utils" / "html_template").resolve()
OUTPUT_FILE_NAME1 = "Cells_categories.parquet"
OUTPUT_FILE_NAME2 = "Cells_numeric_categories.parquet"

METRICS_CSV_OUTPUT_MAPPER = {
    "Cell volume - mean (µm³)": "Cell volume - mean (um^3)",
    "Cell volume - median (µm³)": "Cell volume - median (um^3)",
    "Filtered out cell density (1/100µm²)": "Filtered out cell density (1/100um^2)",
}

MIN_GENES_PER_CELL = 0
MIN_COUNT_PER_CELL = 0
PCA_SOLVER = "arpack"
UMAP_NEIGHBORS = 10
UMAP_PCS = 20
MIN_DIST = 0.5
SPREAD = 1.0
LEIDEN_RESOLUTION = [1.0]
SIZE_X = 216
SIZE_Y = 216
FACTOR = 9.25925925925926
