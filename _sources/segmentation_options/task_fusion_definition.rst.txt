Task Fusion Definition
=========================================================

After the segmentation task(s) are performed, there will likely be overlaps between the different Entity polygons that were 
detected. These overlaps arise from intentionally overlapped image regions, minor overlaps due to polygon post-processing, and 
overlaps due to the same Entity being detected by multiple tasks. There are three supported task fusion options:

- harmonize *(recommended)*
    The harmonize option attempts to find a compromise between the different overlapping  
    geometries. If an overlap is greater than 50% of either Entity, the Entities are merged
    into a single output Entity. If the overlap is less than 50%, the overlapping region is 
    subtracted from the larger Entity.
- union
    Regardless of the amount of overlap between Entities, any overlapping input Entities are 
    fused into a single output Entity.
- larger
    Regardless of the amount of overlap between Entities, if two input Entities overlap, 
    only keep the larger Entity.

Following these fusion operations, two additional checks will be applied.

* min_distance_between_entities
  
  When polygons are subtracted from one another (as they are in the harmonize operation), the space between the cells is zero.
  In order to provide some separation between cells, a minimum distance between these cell can be specified.

* min_final_area

    When polygons are subtracted from one another (as they are in the harmonize operation), the polygon with area removed may 
    fall below the plausible size for a cell. The ``min_final_area`` defines this minimum size; smaller cells are removed from 
    the output.

Usage:

.. code-block:: javascript

    "segmentation_task_fusion": {
        "entity_fusion_strategy": "harmonize",
        "fused_polygon_postprocessing_parameters": {
            "min_distance_between_entities": 1,
            "min_final_area": 500
        }
    }
