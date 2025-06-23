"""
Plot publisher for Live Data Server
"""
try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"
from .plot_publisher import publish_plot, plot1d, plot_heatmap

__all__ = ["publish_plot", "plot1d", "plot_heatmap", "__version__"] 