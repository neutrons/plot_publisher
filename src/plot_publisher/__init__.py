"""
Plot publisher for Live Data Server
"""

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"
from ._plot_publisher import inject_plotlyjs_version, plot1d, plot_heatmap, publish_plot

__all__ = ["plot1d", "plot_heatmap", "publish_plot", "inject_plotlyjs_version", "__version__"]
