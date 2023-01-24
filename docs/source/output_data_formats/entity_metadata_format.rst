.. _entity_metadata_format:

Entity Metadata File Format
=========================================================

Working with the raw geometry information for an entire experiment can require significant time and memory resources. Cell 
metadata is calculated and provided to accelerate some types of geometric operations, such as cell filtering. Entity metadata 
files have the following columns:

* EntityID *(type: int64)* \
    The EntityID of the Entity in the row. The EntityID is guaranteed unique for an Entity type within an \
    experiment, and is also likely to be unique across Entity types and experiments run on an instrument
* fov *(type: int or None)* \
    The field of view index of the Entity.
* volume *(type: float)* \
    The approximate volume of the cell (µm^3). Based on a linear interpolation of each z-layer of the cell geometries to 
    produce a 3D solid. 
* center_x *(type: float)* \
    The x position of the centroid of the Entity in the global coordinate system, units of microns (um).
* center_y *(type: float)* \
    The y position of the centroid of the Entity in the global coordinate system, units of microns (um).
* min_x *(type: float)* \
    The minimum x extent of the Entity geometry in the global coordinate system, units of microns (um).
* max_x *(type: float)* \
    The maximum x extent of the Entity geometry in the global coordinate system, units of microns (um).
* min_y *(type: float)* \
    The minimum y extent of the Entity geometry in the global coordinate system, units of microns (um).
* anisotropy *(type: float)* \
    The ratio of the length of the major axis of the cell to the length of its minor axis (always greater than or equal to 1). 
    A value of 1 represents a circular or square cell.  
* transcript_count *(type: int)* \
    The number of transcripts, including Blanks, that fall within the cell.
* perimeter_area_ratio *(type: float)* \
    The ratio of the perimeter of the cell to its area, calculated at each z-level and averaged across the across occupied 
    z-levels. Higher values correspond with more complex / non-convex shapes. 
* solidity *(type: float)* \
    The ratio of the area of the cell to the area of a convex hull around the cell, calculated at each z-level and averaged 
    across the cell. Lower values correspond with more complex / non-convex shapes.  
