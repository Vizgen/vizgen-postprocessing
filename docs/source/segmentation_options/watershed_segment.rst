Watershed Options
=========================================================

The Watershed segmentation algorithm uses the 3-D watershed implementation in scikit-image 
(``skimage.segmentation.watershed``). Watershed segmentation converts one or more images into seed 
locations and a depth map and fills the depth map "basins" from the seed locations.

Input Data
""""""""""""
Seed channel
    An image channel that will be processed into seeds. The image does not need to show the full \
    extent of the Entity, but should have a high signal-to-noise ratio to allow confident \
    identification of seed locations.

Entity fill channel
    An image channel that will be used to define the boundaries of the Entity. The image may have \
    variegated signal within an Entity, but should fill as much of the Entity as possible. Using \
    DAPI as the fill channel is recommended if identifying Nucleus Entities.

Watershed Model Properties
""""""""""""""""""""""""""""""""
The only property set for the Watershed Model is ``model_dimensions`` and only the default value of "2D" is currently 
supported.

Usage:

.. code-block:: javascript

    "segmentation_properties": {
        "model_dimensions": "2D"
    }

Watershed Model Parameters
""""""""""""""""""""""""""""""""
Seeds for watershed segmentation are identified using the Stardist deep convolutional neural \
network, typically to identify nuclei.

Parameters for Stardist seed identification:

* nuclear_channel *(The image channel that represents nuclei)*
* entity_fill_channel *(The image channel that either fills or outlines the cells)*
* Stardist model *(default is "2D_versatile_fluo")*
  
  Select actual stardist model to use, this parameter could be name of one of the pretrained stardist models, or a path to the 
  model file

Usage:

.. code-block:: javascript

    "segmentation_parameters": {
        "seed_channel": "DAPI",
        "entity_fill_channel": "PolyT"
        "stardist_model": "2D_versatile_fluo"
    }
