CellposeSAM Options
=========================================================

The CellposeSAM plugin (``segmentation_family: "CellposeSAM"``) provides cell segmentation using Cellpose-SAM,
which combines Cellpose 4 flow estimation with the Segment Anything Model (SAM) to refine cell boundaries
[cellposesam_citation1]_ [cellposesam_citation2]_. In the current VPT plugin, this family produces cell polygons
for ``entity_types_detected: ["cell"]`` rather than a separate nucleus output.

.. warning::
    A CUDA-capable GPU is required for production CellposeSAM workloads. Around 6 GB VRAM is a practical minimum for
    typical runs, but exact needs depend on tile size and image dimensions. CPU execution is supported but significantly
    slower.

Installation
""""""""""""

CellposeSAM is **not** included in the base ``vpt`` or ``vpt[all]`` install. Install it in the same Python
environment as ``vpt``:

.. code-block:: bash

    pip install vpt-plugin-cellposesam

Additional plugin documentation and source-install instructions are available in the
`vpt-plugin-cellposesam repository <https://github.com/Vizgen/vpt-plugin-cellposesam>`_.

Input Data
""""""""""""

CellposeSAM accepts one or more image channels as input. A nuclear channel (typically DAPI) and an entity fill
channel (e.g. PolyT) are specified in the segmentation parameters. Additional channels may be provided in
``task_input_data`` to give the model more morphological context.

CellposeSAM Model Properties
""""""""""""""""""""""""""""""""

The CellposeSAM task schema accepts the following keys in ``segmentation_properties``:

``model``
    Required. Expected model identifier, typically ``"cellpose-sam"``. In the current plugin implementation this
    value is primarily metadata for the task specification and logging. If ``custom_weights`` is not set, the plugin
    loads the default bundled Cellpose-SAM weights.

``model_dimensions``
    Required. Accepts ``"2D"`` or ``"3D"``. ``"2D"`` treats each z-plane independently. ``"3D"`` passes the
    selected z-planes as a volume, sets ``z_axis`` and ``channel_axis`` for Cellpose-SAM, and runs the model with
    ``do_3D=True``.

``version``
    Required. Free-form version string, typically ``"latest"``. The current plugin records this value in the JSON
    specification for provenance, but does not use it to select different bundled weights.

``custom_weights``
    Optional. Path to local custom Cellpose-SAM weights. When provided, the plugin loads this file instead of the
    default bundled weights.

Usage:

.. code-block:: javascript

    "segmentation_properties": {
        "model": "cellpose-sam",
        "model_dimensions": "2D",
        "custom_weights": null,
        "version": "latest"
    }

CellposeSAM Model Parameters
""""""""""""""""""""""""""""""""

The CellposeSAM task schema accepts the following keys in ``segmentation_parameters``:

``nuclear_channel``
    Required in normal usage. Name of the input image channel containing nuclear signal, typically DAPI. If both
    ``nuclear_channel`` and ``entity_fill_channel`` are provided, the plugin stacks exactly those two channels in that
    order before inference. If either value is empty, the plugin falls back to using all channels listed in
    ``task_input_data``.

``entity_fill_channel``
    Required in normal usage. Name of the input image channel containing cell body or cell boundary signal, typically a
    stain such as PolyT. It participates in the same channel-selection behavior described for ``nuclear_channel``.

``diameter``
    Required. Expected object diameter in pixels. The plugin passes this value directly to Cellpose-SAM, which uses it
    to set the operating scale of the model.

``flow_threshold``
    Required. Flow consistency threshold passed directly to Cellpose-SAM. Higher values allow more candidate masks to
    pass filtering and generally increase recall; lower values apply stricter filtering.

``cellprob_threshold``
    Required. Cell probability threshold passed directly to Cellpose-SAM. Lower values accept weaker signal and
    generally produce larger or more numerous masks. Higher values suppress weak detections.

``minimum_mask_size``
    Required. Minimum mask area in pixels. Masks smaller than this value are filtered out before polygon conversion.

.. note::
   The plugin validates that any specified ``nuclear_channel`` or ``entity_fill_channel`` is present in
   ``task_input_data`` before execution.

Detailed descriptions of flow and cell-probability thresholds are available in the
`Cellpose documentation <https://cellpose.readthedocs.io/en/latest/settings.html>`_.

Usage:

.. code-block:: javascript

    "segmentation_parameters": {
        "nuclear_channel": "DAPI",
        "entity_fill_channel": "PolyT",
        "diameter": 30,
        "flow_threshold": 0.95,
        "cellprob_threshold": -5.5,
        "minimum_mask_size": 500
    }

Example Segmentation Specification
""""""""""""""""""""""""""""""""""""

A complete single-task CellposeSAM specification with three channels:

.. code-block:: javascript

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
                        "image_channel": "PolyT",
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
                    "mosaic_geometry_file": "cellposesam_mosaic_space.parquet",
                    "micron_geometry_file": "cellposesam_micron_space.parquet",
                    "cell_metadata_file": "cellposesam_cell_metadata.csv"
                }
            }
        ]
    }

References
""""""""""""

.. [cellposesam_citation1] Stringer, C. & Pachitariu, M. (2025). Cellpose-SAM: superhuman generalization for cellular segmentation. *bioRxiv*, 2025.04.28.651001.
.. [cellposesam_citation2] Stringer, C., Wang, T., Michaelos, M., & Pachitariu, M. (2021). Cellpose: a generalist algorithm for cellular segmentation. *Nature methods*, 18(1), 100–106.
