Entity-By-Gene Matrix File Format
=========================================================

Once Entities geometries have been defined, it is possible to use them to count transcripts
within each Entity. These files have EntityIDs in rows and the genes in the gene panel design in columns. The values in the 
table are the sum of the transcripts matching the EntityID (row) and gene name (column). 

In addition to gene panel barcodes that encode genes, the Entity-by-gene matrix also contains information about the number of 
"Blank" barcodes partitioned into each cell. Blank barcodes are decoded combinations of MERFISH spots that do not correspond 
to a known gene or transcript. Blanks may be used in downstream analysis to calculate data quality / confidence metrics.
