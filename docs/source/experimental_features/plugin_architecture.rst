Building a Third-Party Plugin
=========================================================

Overview
---------------------------

The ``vpt`` plugin architecture allows users to run custom cell segmentation algorithms on their data. This plug-and-play
structure gives users the ability to have full customization over the segmentation model and parameters they wish to employ,
so long as it fits the plugin specification and existing workflow.

Vizgen provides the following pre-built plugins:

**Legacy plugins** (available as optional ``vpt`` extras):

- ``vpt-plugin-cellpose`` (`Cellpose repo <https://github.com/Vizgen/vpt-plugin-cellpose>`_) — legacy built-in Cellpose family
- ``vpt-plugin-watershed`` (`Watershed repo <https://github.com/Vizgen/vpt-plugin-watershed>`_) — Watershed family

**Newer plugins** (installed separately):

- ``vpt-plugin-cellpose2`` (`Cellpose2 repo <https://github.com/Vizgen/vpt-plugin-cellpose2>`_) — Cellpose 2 family
- ``vpt-plugin-cellposesam`` (`CellposeSAM repo <https://github.com/Vizgen/vpt-plugin-cellposesam>`_) — CellposeSAM (Cellpose 4 + SAM) family
- ``vpt-plugin-instanseg`` (`InstanSeg repo <https://github.com/Vizgen/vpt-plugin-instanseg>`_) — InstanSeg family

The legacy plugins can be installed individually or together using ``vpt`` extras:

.. code-block:: bash

    pip install vpt[cellpose]     # legacy Cellpose only
    pip install vpt[watershed]    # Watershed only
    pip install vpt[all]          # both legacy plugins

The newer plugins are distributed as separate packages and must be installed into the same Python
environment as ``vpt``:

.. code-block:: bash

    pip install vpt-plugin-cellpose2
    pip install vpt-plugin-cellposesam
    pip install vpt-plugin-instanseg

Each repository linked above also contains additional plugin-specific documentation and source-install instructions for
users who prefer to clone a plugin repository instead of installing from PyPI.

All plugins — legacy and newer — follow the same architecture described below. See :ref:`Installation`
for full details.


Naming and Structure
---------------------------

The **segmentation family** is defined in the :ref:`Segmentation Task Definition` section. With the plugin architecture, 
packages should be named as such, vpt-plugin-<**segmentation family**>. Examples of this include
packages available from Vizgen, such as ``vpt-plugin-cellpose``, ``vpt-plugin-cellpose2``,
``vpt-plugin-cellposesam``, ``vpt-plugin-instanseg``, and ``vpt-plugin-watershed``. Similarly, modules
in the root folder of the plugin need to be of the form, vpt\_plugin\_<**segmentation family**>.

After VPT has found the appropriately named module, vpt\_plugin\_<**segmentation family**>, it will import a sub-module 
named ``segment.py`` which must exist within the vpt\_plugin\_<**segmentation family**> module. In this file is where a 
user will import ``SegmentationBase`` from vpt-core and run mask prediction.

Within the ``segment.py`` module, there needs to exist a ``SegmentationMethod`` class that will inherit the ``SegmentationBase`` class 
from ``vpt-core``. The ``SegmentationMethod`` class will use the segmentation method of the users choice to run prediction and generate 
a segmentation mask. From the generated masks, the user needs to return geometries according to the specification of the 
``SegmentationResult`` class in ``vpt-core``. The user may choose to customize this task or use ``vpt-core`` function, 
``generate_polygons_from_mask()``, to complete the task. The example below shows the
family-agnostic structure expected from a plugin.

.. code-block:: python

    from typing import Dict, Optional, List, Iterable, Union

    import pandas as pd

    from vpt_core.io.image import ImageSet
    from vpt_core.segmentation.polygon_utils import generate_polygons_from_mask
    from vpt_core.segmentation.seg_result import SegmentationResult
    from vpt_core.segmentation.segmentation_base import SegmentationBase
    from vpt_plugin_example import predict, ExampleSegProperties, ExampleSegParameters

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
            properties = ExampleSegProperties(**segmentation_properties)
            parameters = ExampleSegParameters(**segmentation_parameters)
            
            masks = predict.run(images, properties, parameters)
            return generate_polygons_from_mask(masks, polygon_parameters)

The ``run_segmentation()`` method within the ``SegmentationMethod`` class runs the prediction specified in the predict module.
The ``run()`` method and hence ``run_segmentation()`` method takes as input images digested from the segmentation task definition.
The ``images`` object is an instance of the ``ImageSet`` class in ``vpt-core`` which contains information about the images as well as
methods to return the images contained within as a stack for when the model needs to be run on a ``numpy.ndarray`` as in the
``run()`` method in the ``predict`` module.

The ``run_segmentation()`` method within the ``SegmentationMethod`` class returns a ``SegmentationResult`` object that contains cell 
geometries. Upon this object’s creation in ``generate_polygons_from_mask()``, this object translates fields of information 
about each cell and consolidates them into a ``geopandas`` GeoDataFrame that is later saved and can be accessed to visualize 
the predicted cell geometries.

Vignette
---------------------------

As an example, below is a simplified snippet of a ``predict`` module. The code block in the above
**Naming and Structure** section shows how this module is imported and used. Real plugins may select
channels, skip empty z-levels, load bundled or custom weights, and choose between 2D and 3D inference.
Those behaviors are family-specific and should be documented by the plugin itself rather than assumed
by the architecture.

.. note::
   The legacy Cellpose plugin is one concrete implementation of this pattern, but newer plugins
   use different parameter dataclasses and model-loading logic. See the individual plugin reference
   pages under :doc:`Segmentation Options <../segmentation_options/index>` for the current parameter surfaces.

.. code-block:: python

    import numpy as np

    from vpt_core.io.image import ImageSet
    from vpt_plugin_example import ExampleSegProperties, ExampleSegParameters


    def run(
        images: ImageSet,
        properties: ExampleSegProperties,
        parameters: ExampleSegParameters,
    ) -> np.ndarray:
        image = images.as_stack()
        mask = run_model(image, properties=properties, parameters=parameters)
        return mask