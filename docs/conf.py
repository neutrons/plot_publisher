project = 'plot_publisher'
copyright = "Copyright 2025"  # noqa A001
author = "Author Name"

try:
    from plot_publisherpy import __version__
    version = __version__
    release = version
except ImportError:
    version = "0.0.0"
    release = version

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx_rtd_theme',
    'myst_parser',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static'] 
