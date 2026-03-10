"""
Plot publisher for Live Data Server
"""

try:
    from ._version import __version__
except ImportError:
    __version__ = "unknown"
from ._plot_publisher import extract_plot1d_data, inject_plotlyjs_version, plot1d, plot_heatmap, publish_plot

__all__ = ["extract_plot1d_data", "plot1d", "plot_heatmap", "publish_plot", "inject_plotlyjs_version", "__version__"]
