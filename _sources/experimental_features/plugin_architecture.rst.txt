Building a Third-Party Plugin
=========================================================

Overview
---------------------------

The ``vpt`` plugin architecture allows users to run custom cell segmentation algorithms on their data. This plug-and-play 
structure gives users the ability to have full customization over the segmentation model and parameters they wish to employ, 
so long as it fits the plugin specification and existing workflow. The user can always choose to utilize the previously 
supported segmentation techniques, Cellpose and Watershed.   

Currently, Vizgen provides two pre-built plugins for use in segmentation:

- vpt-plugin-cellpose
- vpt-plugin-watershed

These packages, ``vpt-plugin-cellpose`` and ``vpt-plugin-watershed``, use the Cellpose and Watershed techniques respectively. 
Reiterating the Installation section, the packages can be installed individually or together using ``vpt[all]``.

For Cellpose:
    .. code-block:: bash

        pip install vpt[cellpose]

For Watershed:
    .. code-block:: bash

        pip install vpt[watershed]

For all:
    .. code-block:: bash

        pip install vpt[all]


Naming and Structure
---------------------------

The **segmentation family** is defined in the :ref:`Segmentation Task Definition` section. With the plugin architecture, 
packages should be named as such, vpt-plugin-<**segmentation family**>. Examples of this include the two aforementioned 
packages available from Vizgen, ``vpt-plugin-cellpose`` and ``vpt-plugin-watershed``. Similarly, modules 
in the root folder of the plugin need to be of the form, vpt\_plugin\_<**segmentation family**>.

After VPT has found the appropriately named module, vpt\_plugin\_<**segmentation family**>, it will import a sub-module 
named ``segment.py`` which must exist within the vpt\_plugin\_<**segmentation family**> module. In this file is where a 
user will import ``SegmentationBase`` from vpt-core and run mask prediction.

Within the ``segment.py`` module, there needs to exist a ``SegmentationMethod`` class that will inherit the ``SegmentationBase`` class 
from ``vpt-core``. The ``SegmentationMethod`` class will use the segmentation method of the users choice to run prediciton and generate 
a segmentation mask. From the generated masks, the user needs to return geometries according to the specification of the 
``SegmentationResult`` class in ``vpt-core``. The user may choose to customize this task or use ``vpt-core`` function, 
``generate_polygons_from_mask()``, to complete the task. Below is an example of this from the Cellpose plugin.

.. code-block:: python

    from typing import Dict, Optional, List, Iterable, Union

    import pandas as pd

    from vpt_core.io.image import ImageSet
    from vpt_core.segmentation.polygon_utils import generate_polygons_from_mask
    from vpt_core.segmentation.seg_result import SegmentationResult
    from vpt_core.segmentation.segmentation_base import SegmentationBase
    from vpt_plugin_cellpose import predict, CellposeSegProperties, CellposeSegParameters

    class SegmentationMethod(SegmentationBase):
        @staticmethod
        def run_segmentation(
            segmentation_properties: Dict,
            segmentation_parameters: Dict,
            polygon_parameters: Dict,
            result: List[str],
            images: Optional[ImageSet] = None,
            transcripts: Optional[pd.DataFrame] = None,
        ) -> Union[SegmentationResult, Iterable[SegmentationResult]]:
            properties = CellposeSegProperties(**segmentation_properties)
            parameters = CellposeSegParameters(**segmentation_parameters)
            
            masks = predict.run(images, properties, parameters)
            return generate_polygons_from_mask(masks, polygon_parameters)

The ``run_segmentation()`` method within the ``SegmentationMethod`` class runs the prediction specified in the predict module. 
The ``run()`` method and hence ``run_segmentation()`` method takes as input images digested from the segmentation task definition. 
The 'images' is an instance of the ``ImageSet`` class in ``vpt-core`` which contains information about the images as well as 
methods to return the images contained within as a stack for when the model needs to be run on a ``numpy.ndarray`` as in the 
``run()`` method in the ``predict`` module.

The ``run_segmentation()`` method within the ``SegmentationMethod`` class returns a ``SegmentationResult`` object that contains cell 
geometries. Upon this object’s creation in ``generate_polygons_from_mask()``, this object translates fields of information 
about each cell and consolidates them into a ``geopandas`` GeoDataFrame that is later saved and can be accessed to visualize 
the predicted cell geometries.

Vignette
---------------------------

As an example, below is a snippet of the ``predict`` module. The code block in the above **Naming and Structure** section 
shows how this module is imported and used. This module contains the actual Cellpose model and its parameter control.

.. code-block:: python

    import warnings

    import numpy as np
    from cellpose import models

    from vpt_core.io.image import ImageSet
    from vpt_plugin_cellpose import CellposeSegProperties, CellposeSegParameters


    def run(images: ImageSet, properties: CellposeSegProperties, parameters: CellposeSegParameters) -> np.ndarray:
        warnings.filterwarnings("ignore", message=".*the `scipy.ndimage.filters` namespace is deprecated.*")

        is_valid_channels = parameters.nuclear_channel and parameters.entity_fill_channel
        image = (
            images.as_stack([parameters.nuclear_channel, parameters.entity_fill_channel])
            if is_valid_channels
            else images.as_stack()
        )

        empty_z_levels = set()
        for z_i, z_plane in enumerate(image):
            for channel_i in range(z_plane.shape[-1]):
                if z_plane[..., channel_i].std() < 0.1:
                    empty_z_levels.add(z_i)
        if len(empty_z_levels) == image.shape[0]:
            return np.zeros((image.shape[0],) + image.shape[1:-1])

        if properties.custom_weights:
            model = models.CellposeModel(gpu=False, pretrained_model=properties.custom_weights, net_avg=False)
        else:
            model = models.Cellpose(gpu=False, model_type=properties.model, net_avg=False)

        to_segment_z = list(set(range(image.shape[0])).difference(empty_z_levels))
        mask = model.eval(
            image[to_segment_z, ...],
            z_axis=0,
            channel_axis=len(image.shape) - 1,
            diameter=parameters.diameter,
            flow_threshold=parameters.flow_threshold,
            mask_threshold=parameters.mask_threshold,
            resample=False,
            min_size=parameters.minimum_mask_size,
            tile=True,
            do_3D=(properties.model_dimensions == "3D"),
        )[0]
        mask = mask.reshape((len(to_segment_z),) + image.shape[1:-1])
        for i in empty_z_levels:
            mask = np.insert(mask, i, np.zeros(image.shape[1:-1]), axis=0)
        return mask