Cellpose Options
=========================================================

This page documents the **legacy built-in Cellpose** family (``segmentation_family: "Cellpose"``), which uses
Cellpose v.1.0.2 [citation]_.

.. note::
   For the newer Cellpose-derived plugins, see:

   * :doc:`cellpose2_segment` — Cellpose2 plugin with multi-channel support and ``cellprob_threshold``
   * :doc:`cellposesam_segment` — CellposeSAM plugin combining Cellpose 4 with SAM-based segmentation

  The legacy Cellpose plugin source is also available in the
  `vpt-plugin-cellpose repository <https://github.com/Vizgen/vpt-plugin-cellpose>`_. That repository README includes
  additional implementation notes and source-install guidance for users who need to work from a plugin checkout.

In addition 
to supporting  the default model weights (e.g. cyto2, nuclei), ``vpt`` supports custom 
weights that may be more appropriate for a specific tissue type.


Input Data
""""""""""""
The number of channels Cellpose requires is based on the model selected. For the 
nuclei model, only a nuclear channel is necessary (typically DAPI). For the cyto2 
model, both a nuclear and entity fill channel are required.

Cellpose Model Properties
""""""""""""""""""""""""""""""""

The legacy Cellpose task schema accepts the following keys in ``segmentation_properties``:

``model``
  Required. Selects the built-in Cellpose weights to load. Supported values are ``"cyto2"`` for whole-cell
  segmentation and ``"nuclei"`` for nucleus-focused segmentation.

``model_dimensions``
  Required. Accepts ``"2D"`` or ``"3D"``. ``"2D"`` applies the 2D Cellpose model to each z-plane in the
  ``z_layers`` list separately, after which VPT merges the masks into a 3D output. ``"3D"`` passes the selected
  z-planes to Cellpose as a volumetric stack and runs the native 3D model.

``custom_weights``
  Optional. Path to a local custom Cellpose weights file. When provided, the plugin loads this file instead of the
  model zoo weights named by ``model``.

``version``
  Optional. Free-form provenance string stored in the task JSON for record keeping. It does not select a different
  model implementation in the legacy plugin.

Usage:

.. code-block:: javascript

      "segmentation_properties": {
        "model": "cyto2",
        "model_dimensions": "2D",
        "custom_weights": null,
        "version": "latest"
      },

Cellpose Model Parameters
""""""""""""""""""""""""""""""""
The legacy Cellpose task schema accepts the following keys in ``segmentation_parameters``:

``nuclear_channel``
  Required. Name of the input image channel containing nuclear signal, typically DAPI. This channel should also be
  present in ``task_input_data``. For ``"cyto2"`` it supplies Cellpose's nuclear guidance channel; for
  ``"nuclei"`` it is often the main informative channel.

``entity_fill_channel``
  Required. Name of the input image channel containing cell body or cell boundary signal. For whole-cell
  segmentation this is usually a cytoplasmic or membrane-associated stain such as PolyT.

``diameter``
  Required. Expected object diameter in pixels. Cellpose uses this value to internally rescale the image before
  inference. Values that are too small or too large can lead to oversegmentation or undersegmentation.

``flow_threshold``
  Required. Flow consistency threshold passed directly to Cellpose. Higher values allow more candidate masks to pass
  filtering and generally increase recall; lower values apply stricter quality filtering.

``mask_threshold``
  Required. Cell probability threshold used by Cellpose v1. Lower values accept weaker signal and generally produce
  larger or more numerous masks. Higher values suppress weak detections.

``minimum_mask_size``
  Required. Minimum mask area in pixels. Masks smaller than this value are removed before VPT converts them to
  polygons.

Detailed descriptions of each parameter are available in the `Cellpose documentation`_

.. _Cellpose documentation: https://cellpose.readthedocs.io/en/v1.0.2/index.html

Usage:

.. code-block:: javascript

    "segmentation_parameters": {
        "nuclear_channel": "DAPI",
        "entity_fill_channel": "PolyT",
        "diameter": 70,
        "flow_threshold": 0.95,
        "mask_threshold": -5.5,
        "minimum_mask_size": 500
    }

.. [citation] Stringer, C., Wang, T., Michaelos, M., & Pachitariu, M. (2021). Cellpose: a generalist algorithm for cellular segmentation. *Nature methods*, 18(1), 100-106.
