[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
![PyPI](https://img.shields.io/pypi/v/vpt)
[![Coverage Status](https://coveralls.io/repos/github/Vizgen/vizgen-postprocessing/badge.svg?branch=develop&t=EsWr25)](https://coveralls.io/github/Vizgen/vizgen-postprocessing?branch=develop)

# Vizgen Post-processing Tool

The Vizgen Post-processing Tool (VPT) enables users to reprocess and refine the single-cell results of MERSCOPE experiments. 
VPT is a command line tool that emphasizes scalable, reproducible analysis, and can be run on a workstation, a cluster, or 
be deployed in a cloud computing environment.


## Features
- Perform cell segmentation
    - Reproduce standard Vizgen segmentation options
    - Perform reproducible custom segmentation
- Import cell segmentation from other tools
    - Supports geojson and hdf5 formats
- Regenerate single cell data with new segmentation
    - Cell by gene matrix
    - Cell spatial metadata
    - Image intensity in each cell
    - Update MERSCOPE Vizualizer file (vzg)
- Image format conversion
    - Convert large tiff files to single or multi-channel Pyramidal OME-TIFF files
- Nextflow compatible, example pipeline provided


## Installation

Install the tool through your choice of 
- [pip](https://pip.pypa.io/en/stable/getting-started/)
- [Docker](https://docs.docker.com/desktop/extensions-sdk/quickstart/)
- [poetry](https://python-poetry.org/)

To access in-utility help documentation run the process below in the installed environment.
```bash
  vpt --help
```
    
## Usage

VPT accepts two types of inputs to specify how to run segmentation:
- Command line parameters
    - relate to where to find the input data and are expected to vary with each experiment
- Segmentation algorithm .json file parameters
    - describes a series of steps to perform on the input data

Using the same segmentation algorithm on a series of experiments ensures that they are processed identically and reproducibly.

In addition to the user guide, several working segmentation algorithm .json files are provided that can serve either as a 
robust segmentation definition or as a template for a custom workflow.

## Quick start commands:


run-segmentation    ​
- Top-level interface for vpt which invokes the segmentation functionality of the tool.​

prepare-segmentation​
 - Generates a segmentation specification json file to be used for cell segmentation tasks. ​

run-segmentation-on-tile​
 - Executes the segmentation algorithm on a specific tile of the mosaic images.​

compile-tile-segmentation​
- Combines the per-tile segmentation outputs into a single, internally-consistent parquet file containing all of the 
segmentation boundaries found in the experiment.​

derive-entity-metadata​
- Uses the segmentation boundaries to calculate the geometric attributes of each Entity​

partition-transcripts​
- Uses the segmentation boundaries to determine which Entity, if any, contains each detected transcript.​

sum-signals​
- Uses the segmentation boundaries to find the intensity of each mosaic image in each Entity.​

update-vzg​
- Updates an existing .vzg file with new segmentation boundaries and the corresponding expression matrix.​

convert-geometry​
- Converts Entity boundaries produced by a different tool into a vpt compatible parquet file.​

convert-to-ome​
- Transforms the large 16-bit mosaic tiff images produced by the MERSCOPE into a OME pyramidal tiff.​

convert-to-rgb-ome​
- Converts up to three flat tiff images into rgb OME-tiff pyramidal images.​

For more detail on commands and arguments, please see the user guide.

## Documentation

[User Guide](https://vizgen.github.io/vizgen-postprocessing/)

## Feedback

If you encounter issues or bugs, let us know by [submitting an issue!](https://github.com/Vizgen/vizgen-postprocessing/issues)
Please include:

- A quick issue summary
- Steps that caused it to occur
- The exception generated by the code, if applicable
- Specific lines of code, if indicated in the error message


If you have any other feedback or issues, please reach out to your regional Vizgen field application scientist and CC: Vizgen 
Tech Support at techsupport@vizgen.com.

Please include VPT in your subject line along with the above information in the body.

## Contributing & Code of Conduct

We welcome code contributions! Please refer to the [contribution guide](CONTRIBUTING.md) before getting started.

## Authors

- [Vizgen](https://vizgen.com/)

![Logo](https://vizgen.com/wp-content/uploads/2022/12/Vizgen-Logo_Vizgen-BlackColor-.png)

## License

   Copyright 2022 Vizgen, Inc. All Rights Reserved
   
   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
