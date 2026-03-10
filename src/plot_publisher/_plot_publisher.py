#!/usr/bin/env python
import json
import logging
import re
import string
from typing import Dict, List, Optional, Union

import requests
import urllib3

from plot_publisher._configuration import Configuration, read_configuration

logger = logging.getLogger(__name__)


def _getURL(url_template: str, instrument: str, run_number: Union[int, str]) -> str:
    """
    Substitute *instrument* and *run_number* into the given URL template.

    @param url_template: A ``string.Template`` containing the placeholders
                         ``${instrument}`` and ``${run_number}``.
    @param instrument:   Instrument name to inject.
    @param run_number:   Numeric (or string‐convertible) run identifier.
    @return: Fully formatted URL.
    """
    url_template = string.Template(url_template)
    url = url_template.substitute(instrument=instrument, run_number=str(run_number))
    return url


def inject_plotlyjs_version(html_content: str, version: Optional[str] = None) -> str:
    """
    Add a ``plotlyjs-version="<version>"`` attribute to the *first* Plotly ``<div>``
    found in *html_content*.

    @param html_content: HTML string that potentially contains Plotly div elements.
    @param version: The plotly.js version to inject. If None, auto-detects from get_plotlyjs_version().
    @return: The (possibly) modified HTML string with the version attribute injected.
    @raises ValueError: If *html_content* is not a ``str``.
    """
    if not isinstance(html_content, str):
        raise ValueError("html_content must be a string")

    if version is None:
        try:
            from plotly.offline import get_plotlyjs_version

            version = get_plotlyjs_version()
        except ImportError:
            logger.warning("Plotly not available, cannot inject version")
            return html_content

    # Pattern to match any opening div tag with class="plotly-graph-div"
    # This is more specific to plotly divs and should be more reliable
    pattern = r'(<div[^>]*class=["\'][^"\']*plotly-graph-div[^"\']*["\'][^>]*)(>)'

    def add_version_attribute(match):
        opening_tag = match.group(1)
        closing_bracket = match.group(2)

        # Check if plotlyjs-version attribute already exists
        if "plotlyjs-version=" in opening_tag:
            return match.group(0)  # Return unchanged if attribute already exists

        # Add the plotlyjs-version attribute before the closing bracket
        return f'{opening_tag} plotlyjs-version="{version}"{closing_bracket}'

    # Apply the transformation to the first div tag (main plot container)
    modified_html = re.sub(pattern, add_version_attribute, html_content, count=1)

    return modified_html


def publish_plot(
    instrument: str, run_number: Union[int, str], files: Dict[str, str], config: Optional[Configuration] = None
) -> requests.Response:
    """
    Publish one or more files to the plot server.

    @param instrument: Instrument name.
    @param run_number: Run number associated with the data.
    @param files:      ``dict`` of ``{filename: content}``.  HTML strings that look
                       like Plotly divs will have the Plotly version injected.
    @param config:     Optional configuration object or path; if *None* the default
                       configuration is loaded with ``read_configuration()``.
    @return: ``requests.Response`` object from the POST request.
    @raises requests.HTTPError: If the server responds with a non-OK status code.
    @raises ValueError: If input parameters are invalid.
    """
    logger.debug("publish_plot called with instrument=%s, run_number=%s", instrument, run_number)

    # Input validation
    if not instrument or not isinstance(instrument, str):
        raise ValueError("instrument must be a non-empty string")
    if not files or not isinstance(files, dict):
        raise ValueError("files must be a non-empty dictionary")

    # read the configuration if one isn't provided
    if config is None:
        logger.debug("No config provided, reading default configuration")
        config = read_configuration()
    elif isinstance(config, str):
        # assume that it is a filename
        logger.debug("Config is string, reading from file: %s", config)
        config = read_configuration(config)
    elif not isinstance(config, Configuration):
        raise ValueError("config must be a Configuration object, file path string, or None")

    logger.debug("Using config: %s", config)

    # Inject plotlyjs-version into HTML content if it's a plot div
    modified_files = {}
    for key, content in files.items():
        logger.debug("Processing file %s, content type: %s", key, type(content))
        if _is_plotly_html_content(content):
            logger.debug("File %s contains plotly content, injecting version", key)
            # This looks like a Plotly HTML div, inject the version
            modified_files[key] = inject_plotlyjs_version(content)
        else:
            logger.debug("File %s does not contain plotly content", key)
            modified_files[key] = content

    logger.debug("Modified files ready for posting")

    run_number = str(run_number)
    url = _getURL(config.publish_url_template, instrument, run_number)
    logger.info("posting to '%s'", url)

    # Disable only the specific SSL warning we expect, not all warnings
    try:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except AttributeError:
        # Fallback for older urllib3 versions
        urllib3.disable_warnings()

    logger.debug("Making HTTP request with verify_ssl=%s", config.verify_ssl)

    if config.publisher_certificate:
        logger.debug("Using certificate authentication")
        response = requests.post(
            url,
            data={"username": config.publisher_username, "password": config.publisher_password},
            files=modified_files,
            cert=config.publisher_certificate,
            verify=config.verify_ssl,
        )
    else:
        logger.debug("Using basic authentication without certificate")
        response = requests.post(
            url,
            data={"username": config.publisher_username, "password": config.publisher_password},
            files=modified_files,
            verify=config.verify_ssl,
        )

    logger.debug("HTTP request completed with status code: %d", response.status_code)

    if response.status_code != requests.codes.ok:
        logger.error("Publish plot failed with return code: %d", response.status_code)
        response.raise_for_status()  # throw requests.HTTPError error with details
    return response


def _is_plotly_html_content(content: str) -> bool:
    """
    Check if content appears to be Plotly HTML div content.

    @param content: HTML string to check
    @return: True if content looks like Plotly HTML
    """
    if not isinstance(content, str):
        return False

    # More robust detection of plotly content
    plotly_indicators = [
        "<div" in content,
        "id=" in content,
        any(indicator in content for indicator in ["plotly-graph-div", "plotly.js", "Plotly.newPlot"]),
    ]

    return all(plotly_indicators)


def plot1d(
    run_number: Union[int, str],
    data_list: Union[List[float], List[List[float]]],
    data_names: Optional[List[str]] = None,
    x_title: str = "",
    y_title: str = "",
    x_log: bool = False,
    y_log: bool = False,
    instrument: str = "",
    show_dx: bool = True,
    title: str = "",
    publish: bool = True,
) -> Union[requests.Response, str]:
    """
    Generate a 1-D Plotly figure (scatter/error) and optionally publish it.

    @param run_number: Run identifier.
    @param data_list:  See function body for accepted shapes – either a single
                       trace ``[x, y]`` or a list of traces.
    @param data_names: Optional legend labels.
    @param x_title:    X-axis label.
    @param y_title:    Y-axis label.
    @param x_log:      Use log scale on X-axis.
    @param y_log:      Use log scale on Y-axis.
    @param instrument: Instrument name (used if *publish* is True).
    @param show_dx:    Show X error bars when present.
    @param title:      Plot title.
    @param publish:    If ``True`` the plot is sent to the server via
                       ``publish_plot``; otherwise the HTML div is returned.
    @return: ``requests.Response`` when *publish* is True, otherwise the HTML div.
    @raises RuntimeError: If *data_list* is malformed.
    """
    import plotly.graph_objs as go
    from plotly.offline import plot

    # Create traces
    if not isinstance(data_list, list):
        raise RuntimeError("plot1d: data_list parameter is expected to be a list")

    data = []
    show_legend = False

    if len(data_list) >= 2 and not isinstance(data_list[0], list):
        label = ""
        if isinstance(data_names, list) and len(data_names) == 1:
            label = data_names[0]
            show_legend = True

        err_x = {}
        err_y = {}
        if len(data_list) >= 3:
            err_y = dict(type="data", array=data_list[2], visible=True)
        if len(data_list) >= 4:
            err_x = dict(type="data", array=data_list[3], visible=True)
            if show_dx is False:
                err_x["thickness"] = 0

        data = [go.Scatter(name=label, x=data_list[0], y=data_list[1], error_x=err_x, error_y=err_y)]
    else:
        for i in range(len(data_list)):
            if not isinstance(data_list[i], list) or len(data_list[i]) < 2:
                raise RuntimeError(f"plot1d: data_list[{i}] should be a list with at least [x, y] data")
            label = ""
            if isinstance(data_names, list) and len(data_names) == len(data_list):
                label = data_names[i]
                show_legend = True
            err_x = {}
            err_y = {}
            if len(data_list[i]) >= 3:
                err_y = dict(type="data", array=data_list[i][2], visible=True)
            if len(data_list[i]) >= 4:
                err_x = dict(type="data", array=data_list[i][3], visible=True)
                if show_dx is False:
                    err_x["thickness"] = 0
            data.append(go.Scatter(name=label, x=data_list[i][0], y=data_list[i][1], error_x=err_x, error_y=err_y))

    x_layout = dict(
        title=x_title,
        zeroline=False,
        exponentformat="power",
        showexponent="all",
        showgrid=True,
        showline=True,
        mirror="all",
        ticks="inside",
    )
    if x_log:
        x_layout["type"] = "log"
    y_layout = dict(
        title=y_title,
        zeroline=False,
        exponentformat="power",
        showexponent="all",
        showgrid=True,
        showline=True,
        mirror="all",
        ticks="inside",
    )
    if y_log:
        y_layout["type"] = "log"

    layout = go.Layout(
        showlegend=show_legend,
        autosize=True,
        width=600,
        height=400,
        margin=dict(t=40, b=40, l=80, r=40),
        hovermode="closest",
        bargap=0,
        xaxis=x_layout,
        yaxis=y_layout,
        title=title,
    )

    fig = go.Figure(data=data, layout=layout)
    plot_div = plot(fig, output_type="div", include_plotlyjs=False, show_link=False)
    if publish:
        try:
            return publish_plot(instrument, run_number, files={"file": plot_div})
        except requests.HTTPError:
            logger.error("Publish plot failed: HTTP error from server")
            raise  # Re-raise HTTPError so callers can handle it
        except Exception as e:
            logger.error("Publish plot failed: %s", e)
            return None  # Return None for other exceptions
    else:
        return plot_div


def extract_plot1d_data(plot_div: str) -> List[List[List]]:
    """
    Extract data from a Plotly HTML div produced by :func:`plot1d` and reconstruct
    the original ``[[x, y, dy, dx], ...]`` input format.

    Each trace is returned as a plain Python list of lists:

    * ``[x, y]``            – when no error bars are present
    * ``[x, y, dy]``        – when only Y error bars are present
    * ``[x, y, dy, dx]``    – when both X and Y error bars are present

    Error bar arrays are always extracted regardless of their ``visible`` flag.
    All values are returned as plain Python lists.

    @param plot_div: HTML div string produced by :func:`plot1d` with
                    ``publish=False``.
    @return: List of traces, where each trace is ``[x, y]``, ``[x, y, dy]``,
             or ``[x, y, dy, dx]``.
    @raises ValueError: If *plot_div* is not a string, contains no recognisable
                        Plotly data, cannot be JSON-parsed, or has no traces.
    """
    if not isinstance(plot_div, str):
        raise ValueError("plot_div must be a string")

    # Plotly serialises the figure as a JSON argument to Plotly.newPlot or
    # Plotly.react.  Locate the start of the traces array (the first '[' that
    # follows the function call and the div-id argument).
    pattern = r"Plotly\.(?:newPlot|react)\s*\([^,]+,\s*(\[)"
    match = re.search(pattern, plot_div, re.DOTALL)
    if not match:
        raise ValueError("No Plotly data found in the provided div")

    # Use raw_decode starting at the '[' so we get exactly the traces array
    # and stop before the layout/config arguments.
    array_start = match.start(1)
    try:
        traces, _ = json.JSONDecoder().raw_decode(plot_div, array_start)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse Plotly JSON data: {exc}") from exc

    if not isinstance(traces, list) or len(traces) == 0:
        raise ValueError("No traces found in Plotly data")

    result = []
    for trace in traces:
        if not isinstance(trace, dict):
            continue

        x = list(trace.get("x", []))
        y = list(trace.get("y", []))

        # Extract error bar arrays regardless of the visible flag
        dy: List = []
        error_y = trace.get("error_y", {})
        if isinstance(error_y, dict) and "array" in error_y:
            dy = list(error_y["array"])

        dx: List = []
        error_x = trace.get("error_x", {})
        if isinstance(error_x, dict) and "array" in error_x:
            dx = list(error_x["array"])

        if dx:
            result.append([x, y, dy, dx])
        elif dy:
            result.append([x, y, dy])
        else:
            result.append([x, y])

    if not result:
        raise ValueError("No traces found in Plotly data")

    return result


def plot_heatmap(
    run_number,
    x,
    y,
    z,
    x_title="",
    y_title="",
    surface=False,
    x_log=False,
    y_log=False,
    instrument="",
    title="",
    publish=True,
    colorscale="Jet",
):
    """
    Generate a 2-D heat-map (or surface plot) and optionally publish it.

    @param run_number: Run identifier.
    @param x,y,z:      Grid data for the heat-map/surface.
    @param x_title:    X-axis label.
    @param y_title:    Y-axis label.
    @param surface:    When ``True`` render as 3-D surface.
    @param x_log:      Log scale for X.
    @param y_log:      Log scale for Y.
    @param instrument: Instrument name (used if *publish* is True).
    @param title:      Plot title.
    @param publish:    If ``True`` the plot is sent to the server; otherwise the
                       HTML div is returned.
    @param colorscale: Colorscale for the heatmap. Default is "Jet".
    @return: ``requests.Response`` when *publish* is True, otherwise the HTML div.
    """
    import plotly.graph_objs as go
    from plotly.offline import plot

    x_layout = dict(
        title=x_title,
        zeroline=False,
        exponentformat="power",
        showexponent="all",
        showgrid=True,
        showline=True,
        mirror="all",
        ticks="inside",
    )
    if x_log:
        x_layout["type"] = "log"

    y_layout = dict(
        title=y_title,
        zeroline=False,
        exponentformat="power",
        showexponent="all",
        showgrid=True,
        showline=True,
        mirror="all",
        ticks="inside",
    )
    if y_log:
        y_layout["type"] = "log"

    layout = go.Layout(
        showlegend=False,
        autosize=True,
        width=600,
        height=500,
        margin=dict(t=40, b=40, l=80, r=40),
        hovermode="closest",
        bargap=0,
        xaxis=x_layout,
        yaxis=y_layout,
        title=title,
    )

    if surface:
        trace = go.Surface(z=z, x=x, y=y)
    else:
        trace = go.Heatmap(z=z, x=x, y=y, colorscale=colorscale)

    fig = go.Figure(data=[trace], layout=layout)

    plot_div = plot(fig, output_type="div", include_plotlyjs=False, show_link=False)
    if publish:
        try:
            return publish_plot(instrument, run_number, files={"file": plot_div})
        except requests.HTTPError:
            logger.error("Publish plot failed: HTTP error from server")
            raise  # Re-raise HTTPError so callers can handle it
        except Exception as e:
            logger.error("Publish plot failed: %s", e)
            return None  # Return None for other exceptions
    else:
        return plot_div


def extract_heatmap_data(plot_div: str) -> List[List]:
    """
    Extract data from a Plotly HTML div produced by :func:`plot_heatmap` and
    reconstruct the original ``x``, ``y``, ``z`` arrays.

    @param plot_div: HTML div string produced by :func:`plot_heatmap` with
                    ``publish=False``.
    @return: ``[x, y, z]`` where each element is a plain Python list
             (``z`` is a list of rows).
    @raises ValueError: If *plot_div* is not a string, contains no recognisable
                        Plotly data, cannot be JSON-parsed, has no traces, or the
                        first trace contains no ``z`` data.
    """
    if not isinstance(plot_div, str):
        raise ValueError("plot_div must be a string")

    pattern = r"Plotly\.(?:newPlot|react)\s*\([^,]+,\s*(\[)"
    match = re.search(pattern, plot_div, re.DOTALL)
    if not match:
        raise ValueError("No Plotly data found in the provided div")

    array_start = match.start(1)
    try:
        traces, _ = json.JSONDecoder().raw_decode(plot_div, array_start)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse Plotly JSON data: {exc}") from exc

    if not isinstance(traces, list) or len(traces) == 0:
        raise ValueError("No traces found in Plotly data")

    trace = traces[0]
    if not isinstance(trace, dict):
        raise ValueError("No traces found in Plotly data")

    if "z" not in trace:
        raise ValueError("No z data found in trace; the div may not be a heatmap or surface plot")

    x = list(trace.get("x", []))
    y = list(trace.get("y", []))
    z = [list(row) for row in trace["z"]]

    return [x, y, z]


def extract_data(plot_div: str) -> List[List]:
    """
    Extract data from a Plotly HTML div produced by :func:`plot1d` or
    :func:`plot_heatmap` and return it in the original input format.

    The plot type is detected automatically by inspecting the first trace:

    * **Heatmap / surface** (first trace contains a ``z`` key) – delegates to
      :func:`extract_heatmap_data` and returns ``[x, y, z]`` where

      - ``x`` – plain Python list of X-axis values
      - ``y`` – plain Python list of Y-axis values
      - ``z`` – list of rows, each row a plain Python list of Z values

    * **1-D scatter** (no ``z`` key) – delegates to :func:`extract_plot1d_data`
      and returns a list of traces ``[[x, y, ...], ...]`` where each trace is

      - ``[x, y]``         – no error bars
      - ``[x, y, dy]``     – Y error bars only
      - ``[x, y, dy, dx]`` – both Y and X error bars

    All arrays are plain Python lists.  Error bar arrays in 1D plots are always returned
    regardless of their ``visible`` flag.

    @param plot_div: HTML div string produced by :func:`plot1d` or
                    :func:`plot_heatmap` with ``publish=False``.
    @return: ``[x, y, z]`` for heatmap / surface plots, or
             ``[[x, y, ...], ...]`` for 1-D scatter plots.
    @raises ValueError: If *plot_div* is not a string, contains no recognisable
                        Plotly data, cannot be JSON-parsed, or has no traces.
    """
    if not isinstance(plot_div, str):
        raise ValueError("plot_div must be a string")

    pattern = r"Plotly\.(?:newPlot|react)\s*\([^,]+,\s*(\[)"
    match = re.search(pattern, plot_div, re.DOTALL)
    if not match:
        raise ValueError("No Plotly data found in the provided div")

    array_start = match.start(1)
    try:
        traces, _ = json.JSONDecoder().raw_decode(plot_div, array_start)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse Plotly JSON data: {exc}") from exc

    if not isinstance(traces, list) or len(traces) == 0 or not isinstance(traces[0], dict):
        raise ValueError("No traces found in Plotly data")

    if "z" in traces[0]:
        return extract_heatmap_data(plot_div)
    return extract_plot1d_data(plot_div)

