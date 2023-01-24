Biological Entities and Segmentation
=========================================================

The fundamental output of a MERFISH experiment is a list of the spatial locations of RNA molecules. In order to use this list 
of positions to understand biology, the RNA molecules need to be pooled together spatially. The goal of image segmentation for 
MERSCOPE data is to pool together RNA molecules that are in the same biological compartment or "Entity."

The Vizgen Post-processing Tool is concerned with membrane-bound biological entities that can be identified using fluorescent 
stains. In the flow of data through this tool, we preserve Entity-type information using column names and file names. While 
the most commonly identified Entity for most users is a cell, this user guide will refer to "Entities" whenever the specific 
entity type is not relevant to the processing step.
