[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Coverage Status](https://coveralls.io/repos/github/Vizgen/vizgen-postprocessing-internal/badge.svg?branch=develop&t=EsWr25)](https://coveralls.io/github/Vizgen/vizgen-postprocessing-internal?branch=develop)

# Vizgen Post-processing Tool

The Vizgen Post-processing Tool (VPT) is a command-line toolkit for reprocessing and refining the single-cell outputs of
MERSCOPE experiments. VPT supports reproducible segmentation workflows, import of segmentation from external tools, and
regeneration of downstream outputs on workstations, clusters, or cloud environments.


## Features
- Cell segmentation
    - Reproduce standard Vizgen segmentation options
    - Run custom and reproducible segmentation workflows
- Segmentation import
    - Import boundaries produced by external tools
    - Supports GeoJSON and HDF5 formats
- Single-cell output regeneration
    - Cell-by-gene matrix
    - Cell spatial metadata
    - Per-cell image intensity
    - Updated MERSCOPE Visualizer file (VZG)
- Image conversion
    - Convert large TIFF files to single- or multi-channel pyramidal OME-TIFF
- Workflow integration
    - Nextflow-compatible, with an example pipeline provided


## Installation

Install VPT with your preferred method:

### pip
```bash
pip install vpt
```

### Docker
```bash
docker pull vzgdocker/vpt
```

### Poetry
```bash
git clone https://github.com/Vizgen/vizgen-postprocessing
cd vizgen-postprocessing
poetry install
```

To view command help in your installed environment:
```bash
vpt --help
```

## Plugins

VPT supports plugin-based segmentation algorithms.

Install all supported plugins at once:
```sh
pip install vpt[all]
```
if using poetry:
```sh
poetry install --all-extras
```

In most cases, installing only the plugins you need is recommended.

Available plugins:

### watershed
Uses a watershed-based approach with Stardist-derived seeds.

[Watershed Github repository](https://github.com/Vizgen/vpt-plugin-watershed)

Install with:
```sh
pip install vpt-plugin-watershed
```

### cellpose
Interface to Cellpose 1.0.2.

[Cellpose GitHub repository](https://github.com/Vizgen/vpt-plugin-cellpose)

Install with:
```sh
pip install vpt-plugin-cellpose
```

### cellpose2
This plugin is an interface to Cellpose 2.x.

[Cellpose2 GitHub repository](https://github.com/Vizgen/vpt-plugin-cellpose2)

Install with:
```sh
pip install vpt-plugin-cellpose2
```

### cellposesam :star2: New, April 28th, 2026 :star2:
Interface to Cellpose 4.x using the Cellpose-SAM architecture. A GPU is strongly recommended because the model is large and runs very slowly on CPU.

[Cellpose-SAM GitHub repository](https://github.com/Vizgen/vpt-plugin-cellposesam)

Install with:
```sh
pip install vpt-plugin-cellposesam
```

### instanseg :star2: New, April 28th, 2026 :star2:
Interface to the Instanseg segmentation model. It runs on CPU or GPU and can use an arbitrary number of channels.

[Instanseg GitHub repository](https://github.com/Vizgen/vpt-plugin-instanseg)

Install with:
```sh
pip install vpt-plugin-instanseg
```

## Usage

VPT uses two input types to define segmentation runs:

- Command-line parameters
    - Describe input locations and run-specific configuration
- Segmentation algorithm JSON parameters
    - Define the processing steps applied to the input data

Reusing the same segmentation algorithm across experiments helps ensure consistent, reproducible processing.

In addition to the user guide, example segmentation algorithm JSON files are included and can be used directly or adapted
as templates for custom workflows.

## Quick start commands

- `run-segmentation`: Top-level segmentation entrypoint.
- `prepare-segmentation`: Generates a segmentation specification JSON file.
- `run-segmentation-on-tile`: Runs a segmentation algorithm for a specific image tile.
- `compile-tile-segmentation`: Combines per-tile outputs into one internally consistent parquet file.
- `derive-entity-metadata`: Computes geometric attributes for each segmented entity.
- `partition-transcripts`: Assigns each detected transcript to an entity when possible.
- `sum-signals`: Computes image intensity values per entity.
- `update-vzg`: Updates an existing VZG with new boundaries and expression matrix data.
- `convert-geometry`: Converts external boundaries into VPT-compatible parquet format.
- `convert-to-ome`: Converts large 16-bit mosaic TIFF images to pyramidal OME-TIFF.
- `convert-to-rgb-ome`: Converts up to three flat TIFF images into RGB pyramidal OME-TIFF.

For full command usage and options, see the user guide.

## Documentation

[User Guide](https://vizgen.github.io/vizgen-postprocessing/)

## Feedback

If you encounter issues or bugs, please [submit an issue](https://github.com/Vizgen/vizgen-postprocessing/issues).
Please include:

- A short issue summary
- Reproduction steps
- The exception/error output, if applicable
- Relevant code locations, if available


For other feedback, contact your regional Vizgen field application scientist and CC Vizgen Tech Support at
techsupport@vizgen.com.

Please include "VPT" in the subject line.

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
