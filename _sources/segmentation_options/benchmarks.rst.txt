Segmentation Benchmarks
===========================================================

The table below shows example wall-clock runtimes and approximate cell counts for
three segmentation methods on 10 000 × 10 000 pixel crop regions from four
internal MERSCOPE tissue datasets. These datasets are not publicly available;
they are included here to illustrate relative method performance across tissue
types. Each run used the default ``--tile-size 2400 --tile-overlap 200``
settings on a single z-layer.

**Channels used per tissue:**

* **Mouse Brain** — DAPI, PolyT (2 channels)
* **Liver** — DAPI, PolyT, Cellbound3 (3 channels)
* **Lung** — DAPI, PolyT, Cellbound3 (3 channels)
* **Colon** — DAPI, PolyT, Cellbound3 (3 channels)

.. list-table:: Example runtimes and cell counts on 10 000 × 10 000 px tissue crops
   :widths: 18 18 18 18 14
   :header-rows: 1

   * - Tissue
     - Cellpose2 (8 proc)
     - InstanSeg (2 proc)
     - CellposeSAM (2 proc)
     - Approx. Cells (median)
   * - Mouse Brain
     - 1 min 16 s
     - 0 min 59 s
     - 6 min 23 s
     - ~2 700
   * - Liver
     - 1 min 37 s
     - 1 min 38 s
     - 8 min 31 s
     - ~5 100
   * - Lung
     - 1 min 34 s
     - 1 min 52 s
     - 6 min 26 s
     - ~7 400
   * - Colon
     - 1 min 30 s
     - 2 min 01 s
     - 8 min 06 s
     - ~8 800

.. note::
   **Benchmark environment.** All timings were measured on a Linux workstation
   with a mid-range CUDA GPU (8 GB VRAM), 16 logical CPU cores, and 32 GB RAM.
   Cellpose2 was run with 8 parallel processes; InstanSeg and CellposeSAM each
   used 2 processes. Runtime depends strongly on GPU model, CPU count, tile
   size, and image dimensions. Cell counts are the median across the three
   methods (rounded to the nearest hundred) and are intended to convey the
   density of each tissue region. These numbers are provided as representative
   examples and should not be interpreted as guaranteed performance.

See :ref:`system-requirements` for hardware and software prerequisites.
