# Configuration file for the Sphinx documentation builder.

import os
import sys


sys.path.insert(0, os.path.relpath('..'))


# -- Project information -----------------------------------------------------

project = 'Vizgen Post-processing Tool'
copyright = '2022, Vizgen'
author = 'Vizgen'

# -- General configuration ---------------------------------------------------

smartquotes = False
extensions = ['sphinx.ext.autodoc', 'sphinxarg.ext']
templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = ['_static']
html_logo = "_static/Logo_Vizgen_White_Text.svg"
html_css_files = ['css/custom.css']
html_theme_options = {
    'logo_only': True,
    'display_version': True,
}
