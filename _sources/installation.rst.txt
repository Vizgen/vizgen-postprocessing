.. _Installation:

Installation
=========================================================

.. _system-requirements:

System Requirements
    .. list-table::
       :widths: 25 75
       :stub-columns: 1

       * - Python
         - ≥ 3.9, < 3.11
       * - OS
         - Linux (Ubuntu 22.04 recommended), macOS, or Windows
       * - RAM
         - 16 GB minimum; 32 GB or more recommended for large tissue sections
       * - GPU
         - A CUDA-capable GPU is required for production CellposeSAM
           workloads; around 6 GB VRAM is a practical minimum for typical
           runs. Cellpose2 also benefits from GPU acceleration, and
           InstanSeg automatically uses CUDA, MPS, or CPU depending on
           availability
       * - Disk
         - ~5 GB free for model weights, virtual environments, and
           intermediate outputs
       * - System libraries
         - libgl, libvips (≥ 8.12)

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

        pip install vpt

    Install the legacy Cellpose and Watershed extras only if you need those specific
    segmentation families:

    .. code-block:: bash

        pip install vpt[all]

    Users encountering difficulty installing the Python package in their local environment are encouraged to try the Docker
    distribution.

Poetry
    The Vizgen Post-processing Tool ``vpt`` may be installed from source code by cloning the GitHub Repository and installing 
    using poetry:

    .. code-block:: bash

        git clone https://github.com/Vizgen/vizgen-postprocessing
        cd vizgen-postprocessing
        poetry install

    Install the legacy Cellpose and Watershed extras from a source checkout only if
    you need those families:

    .. code-block:: bash

        poetry install --all-extras


Segmentation Plugins
    ``pip install vpt[all]`` (and ``poetry install --all-extras``) install the **legacy** Cellpose and Watershed
    segmentation families that ship as optional extras of the ``vpt`` package.

    Newer segmentation plugins are distributed as **separate packages** and must be installed individually into the
    same Python environment as ``vpt``:

    .. code-block:: bash

        pip install vpt-plugin-cellpose2      # Cellpose 2 family
        pip install vpt-plugin-cellposesam    # CellposeSAM (Cellpose 4 + SAM) family
        pip install vpt-plugin-instanseg      # InstanSeg family

    Each plugin self-registers with VPT at install time. No additional configuration is required — once installed,
    the corresponding ``segmentation_family`` value (``"Cellpose2"``, ``"CellposeSAM"``, or ``"InstanSeg"``) can
    be used in segmentation specification JSON files.

    Repository links and additional plugin documentation:

    * `vpt-plugin-cellpose <https://github.com/Vizgen/vpt-plugin-cellpose>`_ — legacy Cellpose plugin
    * `vpt-plugin-watershed <https://github.com/Vizgen/vpt-plugin-watershed>`_ — Watershed plugin
    * `vpt-plugin-cellpose2 <https://github.com/Vizgen/vpt-plugin-cellpose2>`_ — Cellpose2 plugin
    * `vpt-plugin-cellposesam <https://github.com/Vizgen/vpt-plugin-cellposesam>`_ — CellposeSAM plugin
    * `vpt-plugin-instanseg <https://github.com/Vizgen/vpt-plugin-instanseg>`_ — InstanSeg plugin

    Each repository README includes additional plugin-specific documentation and an alternative source-based
    installation path if you prefer to clone the plugin repository rather than install it from PyPI.

    .. note::
       CellposeSAM vendors its own copy of the Cellpose v4 inference code, so it can coexist with other
       Cellpose-based plugins in the same environment without dependency conflicts.


Post-Install Verification
    After installation, users can verify that ``vpt`` is properly configured by running:
    
    .. code-block:: bash

        vpt --help

    If ``vpt`` was installed through poetry or in a virtual environment, the environment may need to be activated. For 
    example:

    .. code-block:: bash

        poetry run vpt --help




