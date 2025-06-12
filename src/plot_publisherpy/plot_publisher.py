#!/usr/bin/env python
import logging
import os
import string
import requests
import urllib3

from plot_publisherpy.configuration import read_configuration


def _getURL(url_template, instrument, run_number):
    url_template = string.Template(url_template)
    url = url_template.substitute(instrument=instrument, run_number=str(run_number))
    return url


def publish_plot(instrument, run_number, files, config=None):
    # read the configuration if one isn't provided
    if config is None:
        config = read_configuration()
    # verify that it has an attribute that matters
    try:
        config.publish_url_template
    except AttributeError:  # assume that it is a filename
        config = read_configuration(config)

    run_number = str(run_number)
    url = _getURL(config.publish_url_template, instrument, run_number)
    logging.info("posting to '%s'" % url)

    # these next 2 lines are explicity bad - and doesn't seem
    # to do ANYTHING
    # https://urllib3.readthedocs.org/en/latest/security.html
    urllib3.disable_warnings()

    if config.publisher_certificate:
        response = requests.post(
            url,
            data={"username": config.publisher_username, "password": config.publisher_password},
            files=files,
            cert=config.publisher_certificate,
        )
    else:
        response = requests.post(
            url,
            data={"username": config.publisher_username, "password": config.publisher_password},
            files=files,
            verify=False,
        )

    if response.status_code != requests.codes.ok:
        logging.error("Publish plot failed with return code: %d", response.status_code)
        response.raise_for_status()  # throw requests.HTTPError error with details
    return response


def plot1d(
    run_number,
    data_list,
    data_names=None,
    x_title="",
    y_title="",
    x_log=False,
    y_log=False,
    instrument="",
    show_dx=True,
    title="",
    publish=True,
):
    """
    Produce a 1D plot
    @param data_list: list of traces [ [x1, y1], [x2, y2], ...]
    @param data_names: name for each trace, for the legend
    """
    import plotly.graph_objs as go
    from plotly.offline import plot

    # Create traces
    if not isinstance(data_list, list):
        raise RuntimeError("plot1d: data_list parameter is expected to be a list")

    # Catch the case where the list is in the format [x y]
    data = []
    show_legend = False
    if len(data_list) == 2 and not isinstance(data_list[0], list):
        label = ""
        if isinstance(data_names, list) and len(data_names) == 1:
            label = data_names[0]
            show_legend = True
        data = [go.Scatter(name=label, x=data_list[0], y=data_list[1])]
    else:
        for i in range(len(data_list)):
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
        except:  # noqa: E722
            logging.exception("Publish plot failed:")
            return None
    else:
        return plot_div


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
):
    """
    Produce a 2D plot
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
        plot_type = "surface"
    else:
        plot_type = "heatmap"

    trace = go.Heatmap(z=z, x=x, y=y, type=plot_type)
    fig = go.Figure(data=[trace], layout=layout)

    plot_div = plot(fig, output_type="div", include_plotlyjs=False, show_link=False)
    if publish:
        try:
            return publish_plot(instrument, run_number, files={"file": plot_div})
        except:  # noqa: E722
            logging.exception("Publish plot failed:")
            return None
    else:
        return plot_div 