# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import pathlib
import re
import sys


# Import httpx now to prevent an error when importing with sphinx-autodoc-typehints
# and ``set_type_checking_flag = True`` later. ``autodoc_mock_imports = ['httpx']``
# prevents import error but don't document ``Authenticator``, class correctly.


sys.path.insert(0, os.path.abspath("../../src"))


# -- Project information -----------------------------------------------------

project = "audible"
copyright = "2020, mkb79"  # noqa: A001
author = "mkb79"

# The full version, including alpha/beta/rc tags
info = pathlib.Path("../../pyproject.toml").read_text("utf-8")

_version = re.search(f"{'version'} = ['\"]([^'\"]+)['\"]", info)
if _version is None:
    raise Exception("Could not find version in pyproject.toml")
version = _version.group(1)


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.napoleon",
    "sphinx_rtd_theme",
    "sphinx.ext.viewcode",
    "sphinxcontrib.httpdomain",
    "sphinx_autodoc_typehints",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",  # Links to other documentation
    "sphinx_copybutton",        # Copy button for code blocks
    "sphinx.ext.autosectionlabel",  # Reference sections by title
]

# Napoleon
napoleon_numpy_docstring = False

# Autodoc Typehints
set_type_checking_flag = True
typehints_fully_qualified = False
always_document_param_types = True

master_doc = "index"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# =============================================================================
# Type Hints Configuration - Fix for httpx Headers warning
# =============================================================================

# Type Aliases für externe Packages
autodoc_type_aliases = {
    'Headers': 'httpx.Headers',
    'HeaderTypes': 'httpx._types.HeaderTypes',
}

# =============================================================================
# Intersphinx Configuration - Links to external documentation
# =============================================================================
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    # httpx doesn't provide a stable objects.inv, so we skip it
    # Users can still use httpx classes directly without intersphinx
}

# =============================================================================
# Copy Button Configuration
# =============================================================================
copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True
copybutton_only_copy_prompt_lines = True

# Customize button text and behavior
copybutton_selector = "div.highlight pre"
copybutton_copy_empty_lines = False
copybutton_line_continuation_character = "\\"
copybutton_here_doc_delimiter = "EOF"

# Button text labels
copybutton_format_func = None  # Use default formatting

# =============================================================================
# Auto Section Label Configuration
# =============================================================================
autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = 3

# Suppress duplicate label warnings only for CHANGELOG
# (has multiple "Bugfix", "Added", "Changed" sections per version)
suppress_warnings = [
    'autosectionlabel.help/changelog',  # Suppress only CHANGELOG label warnings
]

# =============================================================================
# HTML Theme Options
# =============================================================================
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
    'titles_only': False,
    'style_nav_header_background': '#2980b9',
}

# =============================================================================
# Custom CSS & JavaScript
# =============================================================================
html_css_files = [
    'custom.css',
]

html_js_files = [
    'custom.js',
]

# =============================================================================
# SEO and Metadata
# =============================================================================
html_baseurl = 'https://audible.readthedocs.io/'

html_context = {
    'display_github': True,
    'github_user': 'mkb79',
    'github_repo': 'Audible',
    'github_version': 'master',
    'conf_py_path': '/docs/source/',
}
