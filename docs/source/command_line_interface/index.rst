.. _Command Line Interface:

Command Line Interface
===========================================================

.. argparse::
   :module: vpt.cmd_args
   :func: get_postprocess_parser
   :prog: vpt
   :nodefault:

   --input-images : @replace
         Input images can be specified in one of three ways: 
         
         * The path to a directory of tiff files if the files are named by the MERSCOPE convention. 
             Example: /path/to/files/ 
         * The path to a directory of tiff files including a python formatting string specifying the file name.
             Example: /path/to/files/image_{stain}_z{z}.tif 
         * A regular expression matching the tiff files to be used
             Example: /path/to/files/mosaic_(?P<stain>[\\w|-]+)_z(?P<z>[0-9]+).tif 

         If a formatting string or regular expression are used, it must return values for ``stain`` and ``z`` (as in the 
         examples above).
