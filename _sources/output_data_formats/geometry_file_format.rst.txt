Geometry File Format
=========================================================

MERSCOPE data acquisition and analysis is performed in 3D so the partitioning of transcripts into cells
also needs to be performed in 3D. True 3D geometries are not well supported in standard python geometry 
libraries (e.g. Shapely), so we store the 3D structure of cells (and other Entities)
as 2D slices of the 3D shape. These geometries are organized in a GeoDataFrame in which each row is 
the geometry of an Entity at a given Z-level.

In addition to cell geometries, other types of geometric data about an experiment may be stored in this 
format, including data on user-defined spatial Entities. This GeoDataFrame format is intended to be
extensible to accommodate these new Entity types. In order to conform to the MERSCOPE geometry file format,
we require the presence of a the following columns:

* ID *(type: int64)*
    A unique row identifier for indexing. ID is not globally unique
* EntityID *(type: int64)*
    An integer identifier for a cell or other biological entity identified through spatial analysis. EntityID has the format: 
    analysis timestamp, tile index, task index, geometry index. EntityID is guaranteed to be unique to a biological entity 
    within an analysis region. The use of the analysis timestamp in the ID makes the EntityID likely to be unique across all 
    experiments.  
* Name *(type: string or None)*
    A free-text description of the geometry in the row.
* Type *(type: string)*
    The type of the entity referred in in EntityID.
* ParentID *(type: int64 or None)*
    Entities may be related to one another hierarchically. For example, a Cell Entity may contain a Nucleus Entity.
    These relationships are described using Parent / Child terminology. If this Entity has a Parent, its 
    EntityID may be stored in this column. If it does not have a defined Parent, the column is None.
* ParentType *(string or None)*
    The type of the Parent, if a Parent EntityID is provided. May not be None if ParentID is defined.
* ZLevel *(type: float or None)*
    The z-position of the geometry, expressed in microns.
* ZIndex *(type: int or None)*
    The z-index of the geometry in the 3d stack, useful for querying into transcripts
* Geometry *(type: WKB MultiPolygon)*
    A valid WKB format MultiPolygon that describes the Entity at the given z-level. This column is composed of
    MultiPolygon objects in order to support segmentation methods that produce discontinuous geometries within a z-plane.
    Even if the cell region is continuous and can be described with a single Polygon, it will be stored as a 
    MultiPolygon for consistency.
