
Example: Segmenting the U2OS Small Dataset with Newer Plugins
=============================================================================

This vignette demonstrates how to run cell segmentation on the publicly available
`U2OS small dataset <https://d21zg11mb7aqva.cloudfront.net/202305010900_U2OS_small_set_VMSC00000.zip>`_
using the **CellposeSAM** and **InstanSeg** segmentation plugins.

The U2OS small dataset (3953 × 3960 px, 5 stains, 7 z-levels) is the same dataset
used in the :doc:`segmentation_of_a_local_dataset` vignette. Where that vignette
uses the legacy built-in Cellpose family, this one shows the newer plugin-based
workflows.

.. note::
   CellposeSAM and InstanSeg are **separate packages** — they are not included
   with ``pip install vpt[all]``. Each plugin must be installed individually in
   the same Python environment as VPT. See :ref:`Installation` for details.


Before Beginning: System Setup
""""""""""""""""""""""""""""""""""""""""""""""""

Make sure your environment meets the :ref:`system-requirements` before
proceeding. In particular, CellposeSAM requires a CUDA-capable GPU.

**Download the dataset**

.. code-block:: bash

   wget -q https://d21zg11mb7aqva.cloudfront.net/202305010900_U2OS_small_set_VMSC00000.zip
   unzip -q 202305010900_U2OS_small_set_VMSC00000.zip


CellposeSAM
""""""""""""""""""""""""""""""""""""""""""""""""

Install the Plugin
^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   pip install vpt-plugin-cellposesam

Additional plugin documentation and source-install instructions are available in the
`vpt-plugin-cellposesam repository <https://github.com/Vizgen/vpt-plugin-cellposesam>`_.

Verify that VPT recognises the plugin:

.. code-block:: bash

   vpt --help

Segmentation Specification
^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a file named ``cellposesam_u2os.json`` with the following contents. This
specification selects three stains (DAPI, PolyT, Cellbound1), segments z-layer 3,
and applies CLAHE preprocessing to each channel:

.. code-block:: json

   {
     "experiment_properties": {
       "all_z_indexes": [0, 1, 2, 3, 4, 5, 6],
       "z_positions_um": [1.5, 3.0, 4.5, 6.0, 7.5, 9.0, 10.5]
     },
     "segmentation_tasks": [
       {
         "task_id": 0,
         "segmentation_family": "CellposeSAM",
         "entity_types_detected": ["cell"],
         "z_layers": [3],
         "segmentation_properties": {
           "model": "cellpose-sam",
           "model_dimensions": "2D",
           "custom_weights": null,
           "version": "latest"
         },
         "task_input_data": [
           {
             "image_channel": "DAPI",
             "image_preprocessing": [
               {"name": "normalize", "parameters": {"type": "CLAHE", "clip_limit": 0.01, "filter_size": [100, 100]}}
             ]
           },
           {
             "image_channel": "PolyT",
             "image_preprocessing": [
               {"name": "normalize", "parameters": {"type": "CLAHE", "clip_limit": 0.01, "filter_size": [100, 100]}}
             ]
           },
           {
             "image_channel": "Cellbound1",
             "image_preprocessing": [
               {"name": "normalize", "parameters": {"type": "CLAHE", "clip_limit": 0.01, "filter_size": [100, 100]}}
             ]
           }
         ],
         "segmentation_parameters": {
           "nuclear_channel": "DAPI",
           "entity_fill_channel": "PolyT",
           "diameter": 30,
           "flow_threshold": 0.95,
           "cellprob_threshold": -5.5,
           "minimum_mask_size": 500
         },
         "polygon_parameters": {
           "simplification_tol": 2,
           "smoothing_radius": 10,
           "minimum_final_area": 500
         }
       }
     ],
     "segmentation_task_fusion": {
       "entity_fusion_strategy": "harmonize",
       "fused_polygon_postprocessing_parameters": {
         "min_distance_between_entities": 1,
         "min_final_area": 500
       }
     },
     "output_files": [
       {
         "entity_types_output": ["cell"],
         "files": {
           "run_on_tile_dir": "result_tiles/",
           "mosaic_geometry_file": "cellpose_mosaic_space.parquet",
           "micron_geometry_file": "cellpose_micron_space.parquet",
           "cell_metadata_file": "cellpose_cell_metadata.csv"
         }
       }
     ]
   }

Run Segmentation
^^^^^^^^^^^^^^^^

.. code-block:: bash

   vpt --verbose run-segmentation \
     --segmentation-algorithm cellposesam_u2os.json \
     --input-images '202305010900_U2OS_small_set_VMSC00000/region_0/images/mosaic_(?P<stain>[\w|-]+)_z(?P<z>[0-9]+).tif' \
     --input-micron-to-mosaic 202305010900_U2OS_small_set_VMSC00000/region_0/images/micron_to_mosaic_pixel_transform.csv \
     --output-path u2os_cellposesam_output/ \
     --tile-size 2400 --tile-overlap 200

Expected Results
^^^^^^^^^^^^^^^^

CellposeSAM should detect approximately **800 cell entities** across 4 tiles. The output
directory will contain:

* ``cellpose_micron_space.parquet`` — cell boundary polygons in micron coordinates
* ``cellpose_mosaic_space.parquet`` — cell boundary polygons in mosaic pixel coordinates
* ``result_tiles/`` — per-tile intermediate results

These geometry tables store one row per entity per z-level, so count cells by unique ``EntityID`` rather than total parquet rows.

The ``cell_metadata_file`` entry in the segmentation specification reserves the
downstream metadata filename. The metadata file itself is created later by
``derive-entity-metadata``, not by ``run-segmentation``.

In one representative run on a mid-range CUDA GPU, this completed in approximately
**2 minutes 20 seconds** wall-clock time.


InstanSeg
""""""""""""""""""""""""""""""""""""""""""""""""

Install the Plugin
^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   pip install vpt-plugin-instanseg

Additional plugin documentation and source-install instructions are available in the
`vpt-plugin-instanseg repository <https://github.com/Vizgen/vpt-plugin-instanseg>`_.

Verify that VPT recognises the plugin:

.. code-block:: bash

   vpt --help

Segmentation Specification
^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a file named ``instanseg_u2os.json`` with the following contents. InstanSeg
is channel-invariant, so channel order does not matter. The ``pixel_size`` is set
to 0.108 µm to match the U2OS dataset resolution:

.. code-block:: json

   {
     "experiment_properties": {
       "all_z_indexes": [0, 1, 2, 3, 4, 5, 6],
       "z_positions_um": [1.5, 3.0, 4.5, 6.0, 7.5, 9.0, 10.5]
     },
     "segmentation_tasks": [
       {
         "task_id": 0,
         "segmentation_family": "InstanSeg",
         "entity_types_detected": ["cell"],
         "z_layers": [3],
         "segmentation_properties": {
           "model": "fluorescence_nuclei_and_cells",
           "model_dimensions": "2D",
           "version": "0.1.1",
           "custom_weights": null
         },
         "task_input_data": [
           {
             "image_channel": "DAPI",
             "image_preprocessing": [
               {"name": "normalize", "parameters": {"type": "CLAHE", "clip_limit": 0.01, "filter_size": [100, 100]}}
             ]
           },
           {
             "image_channel": "PolyT",
             "image_preprocessing": [
               {"name": "normalize", "parameters": {"type": "CLAHE", "clip_limit": 0.01, "filter_size": [100, 100]}}
             ]
           },
           {
             "image_channel": "Cellbound1",
             "image_preprocessing": [
               {"name": "normalize", "parameters": {"type": "CLAHE", "clip_limit": 0.01, "filter_size": [100, 100]}}
             ]
           }
         ],
         "segmentation_parameters": {
           "pixel_size": 0.108,
           "normalise": true,
           "target": "all_outputs",
           "rescale_output": true
         },
         "polygon_parameters": {
           "simplification_tol": 2,
           "smoothing_radius": 10,
           "minimum_final_area": 100
         }
       }
     ],
     "segmentation_task_fusion": {
       "entity_fusion_strategy": "harmonize",
       "fused_polygon_postprocessing_parameters": {
         "min_distance_between_entities": 1,
         "min_final_area": 100
       }
     },
     "output_files": [
       {
         "entity_types_output": ["cell"],
         "files": {
           "run_on_tile_dir": "result_tiles/",
           "mosaic_geometry_file": "instanseg_mosaic_space.parquet",
           "micron_geometry_file": "instanseg_micron_space.parquet",
           "cell_metadata_file": "instanseg_cell_metadata.csv"
         }
       }
     ]
   }

Run Segmentation
^^^^^^^^^^^^^^^^

.. code-block:: bash

   vpt --verbose run-segmentation \
     --segmentation-algorithm instanseg_u2os.json \
     --input-images '202305010900_U2OS_small_set_VMSC00000/region_0/images/mosaic_(?P<stain>[\w|-]+)_z(?P<z>[0-9]+).tif' \
     --input-micron-to-mosaic 202305010900_U2OS_small_set_VMSC00000/region_0/images/micron_to_mosaic_pixel_transform.csv \
     --output-path u2os_instanseg_output/ \
     --tile-size 2400 --tile-overlap 200

Expected Results
^^^^^^^^^^^^^^^^

InstanSeg should detect approximately **860 cells** across 4 tiles. The output
directory will contain:

* ``instanseg_micron_space.parquet`` — cell boundary polygons in micron coordinates
* ``instanseg_mosaic_space.parquet`` — cell boundary polygons in mosaic pixel coordinates
* ``result_tiles/`` — per-tile intermediate results

These geometry tables store one row per entity per z-level, so count cells by unique ``EntityID`` rather than total parquet rows.

The ``cell_metadata_file`` entry in the segmentation specification reserves the
downstream metadata filename. The metadata file itself is created later by
``derive-entity-metadata``, not by ``run-segmentation``.

On a mid-range CUDA GPU this run completed in approximately **23 seconds**
wall-clock time. For multi-tissue runtime comparisons, see
:doc:`../segmentation_options/benchmarks`.


Next Steps
""""""""""""""""""""""""""""""""""""""""""""""""

After segmentation, the output parquet files can be used in the standard VPT
workflow (partition transcripts, derive entity metadata, sum signals, update VZG)
exactly as shown in the :doc:`segmentation_of_a_local_dataset` vignette.

For a guide to retraining a Cellpose2 model with manual annotations, see the
:doc:`segmentation_heart_dataset_cellpose2` vignette.

For detailed parameter reference pages, see:

* :doc:`../segmentation_options/cellposesam_segment`
* :doc:`../segmentation_options/instanseg_segment`
* :doc:`../segmentation_options/cellpose2_segment`
