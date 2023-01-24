Segmentation Task Definition
=========================================================

The ``segmentation_tasks`` object in the segmentation algorithm file is a list of tasks. Each task has the following structure:

.. code-block:: javascript
    
    {
        "task_id": 0,
        "segmentation_family": "Cellpose",
        "entity_types_detected": [ ... ],
        "z_layers": [ ... ],
        "segmentation_properties": { ... },
        "task_input_data": [ ... ] ,
        "segmentation_parameters": { ... },
        "polygon_parameters": { ... },
    }

task_id
---------------------------

Each task has an integer index, starting from zero called the ``task_id``. The ``task_id`` is used in the generation of the 
``EntityID`` to ensure uniqueness.

.. note::
    The Vizgen Post-processing Tool ``vpt`` only supports **9** tasks in a single segmentation algorithm. If more tasks are 
    needed, users are encouraged to run ``vpt`` multiple times and combine the segmentation outputs *post hoc*.

segmentation_family
---------------------------

Each task has a ``segmentation_family``. This variable specifies what type of segmentation will be performed and what 
parameters must be provided. The currently supported families are:

* Watershed 
* Cellpose

entity_types_detected
---------------------------
  
A task may detect one or more entities based on ``entity_types_detected``. This is useful for running multiple tools for 
detecting an Entity (e.g. Cells) and combining the output. Supported Entity types are "cell" and "nucleus."

z_layers
---------------------------

The ``z_layers`` variable is a list of which z-index images should be used in this segmentation task. If the type of 
segmentation is 2D and multiple z-indexes are entered, segmentation will be performed on each z-layer sequentially and the 
Entities will be merged into 3D objects at the end of the task. If multiple ``z_layers`` are selected with 2D segmentation, a 
heuristic will be applied to fill in any gaps between segmented layers. *2D segmentation is applied to all z-layers in the 
experiment by default without needing to explicitly specify the behavior.*

Properties and Parameters
---------------------------

Both ``segmentation_properties`` and ``segmentation_parameters`` are specific to the ``segmentation_family`` and are described 
in their own sections.

task_input_data
---------------------------

The ``task_input_data`` list is a list of image channels and per-channel pre-processing steps. This tool allows the 
application of intensity normalization, down-sampling, and/or blurring before performing cell segmentation.

Normalization Options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Filter **name**: "normalize"

Types:

* default *(default if no parameters are specified)* 
  
  default normalization is min-max range normalization. It does not accept any parameters

* CLAHE
  
  Contrast Limited Adaptive Histogram Equalization (CLAHE) is a normalization method for emphasizing *local* contrast in an 
  image at the expense of altering global brightness. CLAHE accepts two parameters:
  
  - clip_limit *(range: 0 - 1)*
  - filter_size *(2 element list, units of pixels)*
  
  For more information, see the `Scikit Image Documentation`_ 

.. _Scikit Image Documentation: https://scikit-image.org/docs/stable/api/skimage.exposure.html#skimage.exposure.equalize_adapthist

Usage:

.. code-block:: javascript

    "image_preprocessing": [
        {
            "name": "normalize",
            "parameters": {
                "type": "CLAHE",
                "clip_limit": 0.01,
                "filter_size": [
                    100,
                    100
                ]
            }
        }
    ]


Blur Filter Options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Filter **name**: "blur"

Types:

* average *(default if no parameters are specified)*
* median
* gaussian

All blur filter types accept a kernel size parameter in units of pixels and are implemented using OpenCV. If the size is
not specified it takes the default value **5px**. 

Usage:

.. code-block:: javascript

    "image_preprocessing": [
        {
            "name": "blur",
            "parameters": {
                "type": "gaussian",
                "size": 21
            }
        }
    ]

Downsample Options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Filter **name**: "downsample"

The downsample filter reduces the size of the images during segmentation to decrease processing time. The only parameter 
passed to the downsample filter is the scale factor, ``scale`` *(default value: 2)*.

Usage:

.. code-block:: javascript

    "image_preprocessing": [
        {
            "name": "downsample",
            "parameters": {
                "scale": 2
            }
        }
    ]

polygon_parameters
---------------------------

The ``polygon_parameters`` are used when converting a foreground / background mask into geometric
shapes describing the outlines of cells. In order to improve computational performance and avoid 
artifacts, smoothing and simplification of Entity geometries is recommended, as is filtering by 
size. All parameters are measured in units of pixels.

Parameters:

* simplification_tol
  
  The acceptable loss of precision when simplifying cell boundaries. Even a small amount of simplification (2 px) dramatically 
  improves processing time.

* smoothing_radius
  
  The size of a smoothing operation comparable to morphologically closing and then opening the cell mask using the same 
  structuring element.

* minimum_final_area
  
  Minimum area of a polygon to retain the cell. Used to filter spurious detections.


Usage:

.. code-block:: javascript

    "polygon_parameters": {
        "simplification_tol": 2,
        "smoothing_radius": 10,
        "minimum_final_area": 500
    }
