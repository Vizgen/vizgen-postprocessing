Cellpose Options
=========================================================

The Cellpose segmentation algorithm uses the Cellpose v.1.0.2 [citation]_. In addition 
to supporting  the default model weights (e.g. cyto2, nuclei), ``vpt`` supports custom 
weights that may be more appropriate for a specific tissue type.


Input Data
""""""""""""
The number of channels Cellpose requires is based on the model selected. For the 
nuclei model, only a nuclear channel is necessary (typically DAPI). For the cyto2 
model, both a nuclear and entity fill channel are required.

Cellpose Model Properties
""""""""""""""""""""""""""""""""

The following model properties are REQUIRED:

* model *("cyto2" or "nuclei")*
* model_dimensions *("2D" or "3D")*
  
  "2D" applies the 2D Cellpose model to all z-planes specified in the ``z_layers`` list seperately and the results are 
  combined into a 3D output. "3D" applies the native-3D Cellpose model to all z-planes specified in the ``z_layers`` list.

The following model properties are OPTIONAL:

* custom_weights *(path to a custom Cellpose weights file, local file system only)*
* version *(any valid string, used for record keeping)*

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
The following model parameters are required:

* nuclear_channel *(The image channel that represents nuclei)*
* entity_fill_channel *(The image channel that either fills or outlines the cells)*
* diameter *(typical cell size, pixels)*
* flow_threshold *(range: 0 to 1, larger values output more cells)*
* mask_threshold *(range: -6 to 6, lower values output larger cells)*
* minimum_mask_size *(minimum cell size, pixels)*

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
