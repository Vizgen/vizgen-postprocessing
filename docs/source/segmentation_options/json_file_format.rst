Segmentation Algorithm JSON File Structure
=========================================================

The json file describing how segmentation should be performed is referred
to as the segmentation algorithm or segmentation_algorithm.json. The structure of the file is
    
.. code-block:: javascript

    {
        "experiment_properties": {
            "all_z_indexes": [0, 1, 2, ... ],
            "z_positions_um": [1.5, 3, 4.5, ... ]
        },
        "segmentation_tasks": [
            {
            "task_id": 0,
            "segmentation_family": "MODEL_NAME",
            "entity_types_detected": [ ... ],
            "z_layers": [ ... ],
            "segmentation_properties": { ... },
            "task_input_data": [ ... ] ,
            "segmentation_parameters": { ... },
            "polygon_parameters": { ... },
            },
            {
            "task_id": 1,
            "segmentation_family": "MODEL_NAME",
            "entity_types_detected": [ ... ],
            "z_layers": [ ... ],
            "segmentation_properties": { ... },
            "task_input_data": [ ... ] ,
            "segmentation_parameters": { ... },
            "polygon_parameters": { ... },
            },
        ],
        "segmentation_task_fusion": { ... },
        "output_files": [
            {
            "entity_types_output": [ ... ],
            "files": { ... }
            }
        ]
    }

The ``experiment_properties`` object holds descriptions of the way the data was collected. Specifically, it must contain a list 
of the z-indexes and z-positions in the data. This data is used to apply 2D segmentation to 3D data and calculate distances on 
the z-axis.

The ``segmentation_tasks`` object holds a list of segmentation tasks to perform. These tasks will be performed sequentially 
and their intermediate outputs saved to a temporary folder. By running different segmentation tools in "tasks" and combining 
their output, it is possible to improve cell detection. For example, combining the results of Cellpose with the ``cyto2`` model 
and the ``nuclei`` model can dramatically improve the segmentation F1 score over either method alone. Each segmentation task 
has options and input data specified separately.

.. note::
    The Vizgen Post-processing Tool ``vpt`` only supports **9** tasks in a single segmentation algorithm. If more tasks are 
    needed, users are encouraged to run ``vpt`` multiple times and combine the segmentation outputs *post hoc*.

The ``segmentation_task_fusion`` object specifies how the geometries produced by each segmentation task should be combined. All 
``segmentation_task_fusion`` options will produce a non-overlapping set of valid geometries.

The ``output_files`` object specifies which entity types should be written to disk in the output folder and the file names 
they should receive.
