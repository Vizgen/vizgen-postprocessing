InstanSeg Options
=========================================================

The InstanSeg plugin (``segmentation_family: "InstanSeg"``) provides cell and nucleus segmentation using the
InstanSeg architecture [instanseg_citation]_, a channel-invariant model that can accept a variable number of input
image channels without retraining. This makes it straightforward to use with different panel configurations.

Installation
""""""""""""

InstanSeg is **not** included in the base ``vpt`` or ``vpt[all]`` install. Install it in the same Python
environment as ``vpt``:

.. code-block:: bash

    pip install vpt-plugin-instanseg

Additional plugin documentation and source-install instructions are available in the
`vpt-plugin-instanseg repository <https://github.com/Vizgen/vpt-plugin-instanseg>`_.

.. note::
    InstanSeg automatically selects CUDA, then MPS, then CPU based on runtime availability.

Input Data
""""""""""""

InstanSeg accepts a variable number of image channels. The model is channel-invariant, so you can provide any
combination of channels in ``task_input_data`` (e.g. DAPI, PolyT, Cellbound markers). All channels listed are
passed to the model as a multi-channel input.

InstanSeg Model Properties
""""""""""""""""""""""""""""""""

The InstanSeg task schema accepts the following keys in ``segmentation_properties``:

``model``
    Required. Name of the bundled InstanSeg model to download and load when ``custom_weights`` is not set. A common
    value is ``"fluorescence_nuclei_and_cells"``.

``model_dimensions``
    Required. Must be ``"2D"``. The current plugin supports 2D inference only. Each selected z-plane is segmented
    independently and VPT merges the per-plane masks into a 3D output structure.

``version``
    Required. Version string for the bundled model. Use ``"latest"`` to let the plugin resolve the newest available
    bundled model version, or pin an explicit version such as ``"0.1.1"`` for reproducibility.

``custom_weights``
    Optional. Path to a local TorchScript ``.pt`` file. When set, the plugin loads this file directly and ignores the
    ``model`` and ``version`` fields. The file must exist on disk.

.. note::
   The plugin rejects unrecognized keys in ``segmentation_properties`` and validates that ``custom_weights`` exists if
   it is provided.

Usage:

.. code-block:: javascript

    "segmentation_properties": {
        "model": "fluorescence_nuclei_and_cells",
        "model_dimensions": "2D",
        "version": "latest",
        "custom_weights": null
    }

InstanSeg Model Parameters
""""""""""""""""""""""""""""""""

All InstanSeg keys in ``segmentation_parameters`` are optional because the plugin defines defaults for each one:

``pixel_size``
    Optional. Default: ``0.1``. Positive image pixel size in microns. InstanSeg uses this value to rescale images to
    the resolution the model was trained on. Incorrect values change the apparent object scale seen by the model.

``normalise``
    Optional. Default: ``true``. Enables InstanSeg's own percentile-style input normalization during inference. This
    is independent of any VPT preprocessing configured in ``task_input_data``.

``target``
    Optional. Default: ``"all_outputs"``. Controls which mask layer the plugin returns to VPT. Valid values are
    ``"all_outputs"``, ``"nuclei"``, and ``"cells"``.

``rescale_output``
    Optional. Default: ``true``. If enabled, the plugin rescales the predicted masks back to the original image
    coordinate space after inference. If disabled, masks remain in the model's inference scale.

**Understanding the** ``target`` **parameter:**

The ``target`` parameter determines what the InstanSeg model segments:

* ``"nuclei"`` — Segment nuclei only.
* ``"cells"`` — Segment whole cells only.
* ``"all_outputs"`` — Segment both nuclei and cells. When this option is used, the plugin returns the **cell**
  boundaries to VPT as the primary segmentation output.

In most use cases, ``"all_outputs"`` is recommended because jointly predicting nuclei and cells allows the model
to leverage both signals for more accurate cell boundaries.

.. note::
    Before execution, the plugin rejects unrecognized ``segmentation_parameters`` keys, requires ``pixel_size`` to be a
    positive number when provided, and requires ``target`` to be one of ``all_outputs``, ``nuclei``, or ``cells``.

Usage:

.. code-block:: javascript

    "segmentation_parameters": {
        "pixel_size": 0.1,
        "normalise": true,
        "target": "all_outputs",
        "rescale_output": true
    }

Example Segmentation Specification
""""""""""""""""""""""""""""""""""""

A complete single-task InstanSeg specification with two channels:

.. code-block:: javascript

    {
        "experiment_properties": {
            "all_z_indexes": [0, 1, 2, 3, 4, 5, 6],
            "z_positions_um": [1.5, 3, 4.5, 6, 7.5, 9, 10.5]
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
                    "version": "latest",
                    "custom_weights": null
                },
                "task_input_data": [
                    {
                        "image_channel": "PolyT",
                        "image_preprocessing": [
                            {"name": "normalize", "parameters": {"type": "CLAHE", "clip_limit": 0.01, "filter_size": [100, 100]}}
                        ]
                    },
                    {
                        "image_channel": "DAPI",
                        "image_preprocessing": [
                            {"name": "normalize", "parameters": {"type": "CLAHE", "clip_limit": 0.01, "filter_size": [100, 100]}}
                        ]
                    }
                ],
                "segmentation_parameters": {
                    "pixel_size": 0.1,
                    "normalise": true,
                    "target": "all_outputs",
                    "rescale_output": true
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
                    "mosaic_geometry_file": "instanseg_mosaic_space.parquet",
                    "micron_geometry_file": "instanseg_micron_space.parquet",
                    "cell_metadata_file": "instanseg_cell_metadata.csv"
                }
            }
        ]
    }

References
""""""""""""

.. [instanseg_citation] Goldsborough, T., et al. (2024). InstanSeg: an embedding-based instance segmentation algorithm optimized for accurate, efficient and portable cell segmentation. *arXiv preprint arXiv:2408.15954*.
