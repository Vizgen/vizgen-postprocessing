VZG File Format 
=========================================================

In addition to exporting raw data about each experiment in open formats (csv, tiff, parquet), 
the MERSCOPE analysis software exports a compiled and compressed version of this data 
appropriate for visualization in the MERSCOPE Desktop Vizualizer software (.vzg file). If the 
Vizgen Post-processing tool is used to generate new Entity geometries, a new Cell-by-Entity 
matrix, etc., this data may be repackaged into a new .vzg file using ``update-vzg``. Reading 
and writing .vzg files is only supported by Vizgen software.
