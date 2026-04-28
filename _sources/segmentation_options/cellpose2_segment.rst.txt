Cellpose2 Options
=========================================================

The Cellpose2 plugin (``segmentation_family: "Cellpose2"``) provides segmentation using newer Cellpose model weights
and introduces multi-channel input via the ``channel_map`` property [cellpose2_citation]_. Unlike the :doc:`legacy
built-in Cellpose family <cellpose_segment>`, Cellpose2 uses ``cellprob_threshold`` instead of ``mask_threshold`` and
supports mapping multiple image channels to the model's RGB input.

Installation
""""""""""""

Cellpose2 is **not** included in the base ``vpt`` or ``vpt[all]`` install. Install it in the same Python environment
as ``vpt``:

.. code-block:: bash

    pip install vpt-plugin-cellpose2

Additional plugin documentation, example algorithm JSON files, and source-install instructions are available in the
`vpt-plugin-cellpose2 repository <https://github.com/Vizgen/vpt-plugin-cellpose2>`_.

Input Data
""""""""""""

The number and identity of input channels is controlled by the ``channel_map`` property. Each key in the map
(``red``, ``green``, ``blue``) specifies which image channel is assigned to that color input of the model. Channels
listed in the map must also appear in the ``task_input_data`` list so that the corresponding images are loaded and
preprocessed.

For the **nuclei** model, typically only a nuclear channel (e.g. DAPI) is needed. For the **cyto2** model, a nuclear
channel and one or more entity fill channels are recommended.

Cellpose2 Model Properties
""""""""""""""""""""""""""""""""

The Cellpose2 task schema accepts the following keys in ``segmentation_properties``:

``model_dimensions``
        Required. Accepts ``"2D"`` or ``"3D"``. ``"2D"`` applies the 2D Cellpose model to each selected z-plane
        separately and VPT merges the masks into a 3D output. ``"3D"`` passes the selected z-planes as a volumetric stack
        and runs Cellpose with ``do_3D=True``.

``channel_map``
        Required. Dictionary mapping ``red``, ``green``, and ``blue`` to image channel names from ``task_input_data``.
        The plugin builds an RGB image in that exact order before calling Cellpose. Set a color entry to an empty string
        ``""`` to leave that plane empty; the plugin fills unused color planes with zeros.

``model``
        Optional when ``custom_weights`` is set; otherwise required. Selects built-in Cellpose weights such as
        ``"cyto2"`` or ``"nuclei"``.

``custom_weights``
        Optional. Path to a local custom Cellpose weights file. When present, the plugin loads this file and ignores the
        built-in model named by ``model``.

.. note::
     Cellpose2 does not define a ``version`` field in ``segmentation_properties``. Before execution, the plugin validates
     that every non-empty ``channel_map`` entry appears in ``task_input_data`` and that at least one of ``model`` or
     ``custom_weights`` is set.

Usage:

.. code-block:: javascript

    "segmentation_properties": {
        "model": "cyto2",
        "model_dimensions": "2D",
        "custom_weights": null,
        "channel_map": {
            "red": "Cellbound1",
            "green": "Cellbound3",
            "blue": "DAPI"
        }
    }

Cellpose2 Model Parameters
""""""""""""""""""""""""""""""""

The Cellpose2 task schema accepts the following keys in ``segmentation_parameters``:

``nuclear_channel``
    Required. Selects the second Cellpose input channel, typically a nuclear stain such as DAPI. Accepted values are
    an image channel listed in ``task_input_data``, one of the mapped color names ``red``, ``green``, or ``blue``,
    or the special values ``all`` and ``grayscale``. Both ``all`` and ``grayscale`` resolve to Cellpose's grayscale
    input channel.

``entity_fill_channel``
    Required. Selects the first Cellpose input channel used for cell body or boundary signal. It accepts the same value
    forms as ``nuclear_channel``: a task input channel name, a mapped color name, or the special values ``all`` and
    ``grayscale``. In practice, ``all`` or ``grayscale`` are useful when a custom model was trained on a composite
    signal rather than a single stain.

``diameter``
    Required. Expected object diameter in pixels. The plugin passes this value directly to Cellpose, which uses it to
    rescale imagery before inference. Incorrect values can materially change mask size and mask count.

``flow_threshold``
    Required. Flow consistency threshold passed directly to Cellpose. Higher values allow more candidate masks to pass
    filtering and generally increase recall; lower values are stricter.

``cellprob_threshold``
    Required. Cell probability threshold passed directly to Cellpose2. Lower values accept weaker signal and generally
    produce larger or more numerous masks. Higher values suppress weak detections.

``minimum_mask_size``
    Required. Minimum mask area in pixels. The plugin passes this value as Cellpose ``min_size`` and removes masks
    smaller than this threshold before polygon generation.

.. note::
   Before execution, the plugin validates that ``task_input_data`` contains at least one channel and that both
   ``nuclear_channel`` and ``entity_fill_channel`` resolve to valid inputs.

Detailed descriptions of flow and cell-probability thresholds are available in the
`Cellpose documentation <https://cellpose.readthedocs.io/en/latest/settings.html>`_.

Usage:

.. code-block:: javascript

    "segmentation_parameters": {
        "nuclear_channel": "DAPI",
        "entity_fill_channel": "all",
        "diameter": 70,
        "flow_threshold": 0.95,
        "cellprob_threshold": -5.5,
        "minimum_mask_size": 500
    }

Example Segmentation Specification
""""""""""""""""""""""""""""""""""""

A complete single-task Cellpose2 specification using the ``cyto2`` model with three channels:

.. code-block:: javascript

    {
        "experiment_properties": {
            "all_z_indexes": [0, 1, 2, 3, 4, 5, 6],
            "z_positions_um": [1.5, 3, 4.5, 6, 7.5, 9, 10.5]
        },
        "segmentation_tasks": [
            {
                "task_id": 0,
                "segmentation_family": "Cellpose2",
                "entity_types_detected": ["cell"],
                "z_layers": [3],
                "segmentation_properties": {
                    "model": "cyto2",
                    "model_dimensions": "2D",
                    "custom_weights": null,
                    "channel_map": {
                        "red": "Cellbound1",
                        "green": "Cellbound3",
                        "blue": "DAPI"
                    }
                },
                "task_input_data": [
                    {
                        "image_channel": "Cellbound1",
                        "image_preprocessing": [
                            {"name": "normalize", "parameters": {"type": "CLAHE", "clip_limit": 0.01, "filter_size": [100, 100]}}
                        ]
                    },
                    {
                        "image_channel": "Cellbound3",
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
                    "nuclear_channel": "DAPI",
                    "entity_fill_channel": "all",
                    "diameter": 70,
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
                    "mosaic_geometry_file": "cellpose2_mosaic_space.parquet",
                    "micron_geometry_file": "cellpose2_micron_space.parquet",
                    "cell_metadata_file": "cellpose2_cell_metadata.csv"
                }
            }
        ]
    }

.. seealso::
   The :doc:`/analysis_vignettes/segmentation_heart_dataset_cellpose2` vignette demonstrates Cellpose2 with
   custom-retrained weights on a heart tissue dataset.

References
""""""""""""

.. [cellpose2_citation] Pachitariu, M. & Stringer, C. (2022). Cellpose 2.0: how to train your own model. *Nature methods*, 19(12), 1634–1641.
