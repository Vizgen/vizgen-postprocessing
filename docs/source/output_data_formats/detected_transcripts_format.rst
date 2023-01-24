Detected Transcripts File Format
=========================================================

The location of decoded MERFISH targets are stored in a csv file called ``detected_transcripts.csv``.
All ``detected_transcripts.csv`` files have the following columns:

* unlabeled *(type: int)*
    A numeric index that uniquely identifies a transcript within a field of view. The index is non-consecutive and ascending 
    within each field of view. 
* barcode_id *(type: int)*
    The row index of the identified transcript “barcode” in the codebook file (zero indexed).
* global_x *(type: float)*
    The x position of the transcript in the global coordinate system, units of microns (um).
* global_y *(type: float)*
    The y position of the transcript in the global coordinate system, units of microns (um).
* global_z *(type: float)*
    The index of the z position of the transcript in the experimental image stack.
* x *(type: float)*
    The x position of the transcript in the field of view (fov) coordinate system, units of pixels.
* y *(type: float)*
    The y position of the transcript in the field of view (fov) coordinate system, units of pixels.
* fov *(type: int)*
    The index of the field of view in which the transcript was imaged (zero indexed). fov and barcode_id are a composite 
    primary key for the detected_transcripts.csv table. 
* gene *(type: string)*
    The human readable name of the gene this transcript is associated with. Gene is derived from the “name” column of the 
    codebook file. 
* transcript_id *(type: int64)*
    A unique identifier of the gene that this transcript is associated with. transcript_id is derived from the “id” column 
    of the codebook file. 

Following segmentation, the user may choose to append a column to the table to store the EntityID an Entity that contains each
transcript. If the transcript is not contained by an Entity, the EntityID will be -1.
