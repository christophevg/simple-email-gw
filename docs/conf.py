# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# Add project source to path
sys.path.insert(0, os.path.abspath("../src"))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "simple-email-gw"
copyright = "2026, Christophe VG"
author = "Christophe VG"
release = "0.1.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
  "myst_parser",
  "sphinx.ext.autodoc",
  "sphinx.ext.napoleon",
  "sphinx.ext.viewcode",
  "sphinx.ext.intersphinx",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
html_title = "simple-email-gw"
html_short_title = "simple-email-gw"

# -- Options for MyST parser ------------------------------------------------
# https://myst-parser.readthedocs.io/en/latest/configuration.html

myst_enable_extensions = [
  "colon_fence",
  "deflist",
  "html_admonition",
]

# -- Options for autodoc ----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html

autodoc_typehints = "description"
autodoc_member_order = "bysource"
autodoc_default_options = {
  "members": True,
  "undoc-members": True,
  "show-inheritance": True,
}

# -- Options for napoleon ----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html

napoleon_google_docstring = True
napoleon_numpy_docstring = False

# -- Options for intersphinx ------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html

intersphinx_mapping = {
  "python": ("https://docs.python.org/3", None),
  "pydantic": ("https://docs.pydantic.dev/latest/", None),
}
