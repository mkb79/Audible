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

# No custom static files are used, so html_static_path is left unset. Setting it
# to a directory that does not exist makes Sphinx emit a warning on every build.


# -- Pending changes on the changelog page -----------------------------------

# Inject "what the next release will contain" at the top of the changelog page,
# generated from this checkout's commits. See tools/unreleased_docs.py: it only
# reads git, writes nothing, and degrades to showing nothing on any failure.
sys.path.insert(0, os.path.abspath("../../tools"))
from sphinx.application import Sphinx  # noqa: E402

import unreleased_docs  # noqa: E402


_UNRELEASED_MARKER = "<!-- unreleased -->"
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _inject_unreleased(app: Sphinx, docname: str, source: list[str]) -> None:
    """Replace the changelog page's marker with the pending-changes block.

    Args:
        app: The Sphinx application (unused).
        docname: The document being read.
        source: A single-element list holding the document's source, modified
            in place per the ``source-read`` contract.
    """
    if docname != "misc/changelog":
        return
    source[0] = source[0].replace(
        _UNRELEASED_MARKER, unreleased_docs.fragment(_REPO_ROOT), 1
    )


def setup(app: Sphinx) -> None:
    """Connect the changelog injection to Sphinx.

    Args:
        app: The Sphinx application.
    """
    app.connect("source-read", _inject_unreleased)
