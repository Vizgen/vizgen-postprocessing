.. _Installation:

Installation
=========================================================

Docker Image
    In order to support a completely reproducible analysis environment, Vizgen provides a Docker image of the Vizgen 
    Post-processing Tool ``vpt`` that can be deployed locally, in a high-performance compute (HPC) environment, or in the 
    cloud. The docker image contains ``vpt`` and all dependencies, as well as:

    * Nextflow
    * AWS CLI v2 
    * Example segmentation algorithm json files 
    * Simple Nextflow pipeline suitable for deploying ``vpt`` in a HPC environment

    The docker image may be downloaded using docker pull:

    .. code-block:: bash

        docker pull vzgdocker/vpt

Python Package Index
    The Vizgen Post-processing Tool ``vpt`` is available as a Python package. The package may be installed using pip:

    .. code-block:: bash

        pip install vpt[all]

    The functionality of ``vpt`` requires the following system libraries:

    * libgl
    * libvips (version >=8.12)
    
    These libraries are available on Windows, MacOS, or Linux. Development and testing of ``vpt`` is done using Ubuntu 22.04. 
    Users encountering difficulty installing the Python package in their local environment are encouraged to try the Docker 
    distribution.

Poetry
    The Vizgen Post-processing Tool ``vpt`` may be installed from source code by cloning the GitHub Repository and installing 
    using poetry:

    .. code-block:: bash

        git clone https://github.com/Vizgen/vizgen-postprocessing
        cd vizgen-postprocessing
        poetry install --all-extras


Post-Install Verification
    After installation, users can verify that ``vpt`` is properly configured by running:
    
    .. code-block:: bash

        vpt --help

    If ``vpt`` was installed through poetry or in a virtual environment, the environment may need to be activated. For 
    example:

    .. code-block:: bash

        poetry run vpt --help




