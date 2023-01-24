Overview
=========================================================

The Vizgen Post-processing Tool ``vpt`` accepts two types of inputs to specify
how to run segmentation:

- Command line arguments
- Segmentation algorithm .json file parameters

Command line arguments generally relate to properties of the computing platform running ``vpt`` and are expected to vary with 
each experiment. For example, the location of files and optimal number of parallel processes depend on the  computer running 
``vpt`` and are set with command line arguments. These arguments are described in the :ref:`Command Line Interface` section.

In contrast, the segmentation algorithm .json file describes a series of steps to perform on the input data that are 
independent of the computing environment. Using the same segmentation algorithm on a series of experiments ensures that they 
are processed identically and reproducibly.

In addition to this documentation, several working example segmentation algorithm json files are provided that can serve 
either as a ready-made segmentation definition, or as a template for a custom workflow. These files are available on the 
``vpt`` GitHub Repository (https://github.com/Vizgen/vizgen-postprocess) or in the Docker Image.
