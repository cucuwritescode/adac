#created by Facundo Franchino June 2026
"""adac documentation build configuration."""

import os
import sys

#put the package on the path so autodoc can import it
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import adac  # noqa: E402

#project information
project = "adac"
copyright = "2026, Facundo Franchino"
author = "Facundo Franchino"
version = adac.__version__
release = adac.__version__

#general configuration
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx_design",
    "sphinx_copybutton",
]

#autodoc settings
autodoc_default_options = {"members": True, "undoc-members": True}
autodoc_mock_imports = ["flamo", "torch"]
autosummary_generate = True

#napoleon settings (google / numpy docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True

#intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}

#source settings
source_suffix = ".rst"
master_doc = "index"
language = "en"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

#pygments
pygments_style = "friendly"
highlight_language = "python3"

#html output
html_theme = "pydata_sphinx_theme"
html_title = "adac"

html_theme_options = {
    "navbar_align": "content",
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/cucuwritescode/adac",
            "icon": "fa-brands fa-square-github",
            "type": "fontawesome",
        },
    ],
    "show_toc_level": 2,
    "navigation_with_keys": True,
}

html_context = {"default_mode": "light"}
html_sidebars = {"**": []}
