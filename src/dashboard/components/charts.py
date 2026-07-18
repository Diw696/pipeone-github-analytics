"""
Charts Component
================
Renders Plotly charts inside Streamlit.

Rules:
  - No database calls in this module.
  - Accepts only DataFrames and scalar config arguments.
  - All chart configuration and layout is here; pages only call functions.
  - use_container_width=True on all charts for responsive layout.

Author: PipeOne Project
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ---------------------------------------------------------------------------
# Shared chart config
# ---------------------------------------------------------------------------

_MARGIN = dict(l=20, r=20, t=40, b=20)
_HEIGHT = 380


def render_line_chart(
    df: pd.DataFrame,
    x: str,
    y: str | list[str],
    title: str,
    x_label: str = "",
    y_label: str = "",
    color: str | None = None,
) -> None:
    """
    Render a Plotly line chart.

    Args:
        df:      Source DataFrame
        x:       Column name for x-axis
        y:       Column name(s) for y-axis
        title:   Chart title
        x_label: Optional x-axis label override
        y_label: Optional y-axis label override
        color:   Optional column to use for color grouping
    """
    fig = px.line(
        df,
        x=x,
        y=y,
        color=color,
        title=title,
        labels={x: x_label or x, **(dict(value=y_label) if y_label else {})},
        height=_HEIGHT,
    )
    fig.update_layout(margin=_MARGIN, legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)


def render_area_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: str | None = None,
    color_label: str = "",
) -> None:
    """
    Render a Plotly filled-area chart.

    Args:
        df:          Source DataFrame
        x:           Column name for x-axis
        y:           Column name for y-axis
        title:       Chart title
        color:       Optional column for color grouping (multi-line)
        color_label: Optional legend title for the color column
    """
    fig = px.area(
        df,
        x=x,
        y=y,
        color=color,
        title=title,
        height=_HEIGHT,
    )
    if color_label:
        fig.update_layout(legend_title_text=color_label)
    fig.update_layout(margin=_MARGIN)
    st.plotly_chart(fig, use_container_width=True)


def render_bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str | list[str],
    title: str,
    barmode: str = "group",
    orientation: str = "v",
    color: str | None = None,
    width: float | None = None,
) -> None:
    """
    Render a Plotly bar chart (grouped or stacked).

    Args:
        df:          Source DataFrame
        x:           Column name for x-axis
        y:           Column name(s) for y-axis
        title:       Chart title
        barmode:     "group" (default) or "stack"
        orientation: "v" (vertical, default) or "h" (horizontal)
        color:       Optional column for color grouping
        width:       Optional width of the bars (float)
    """
    fig = px.bar(
        df,
        x=x,
        y=y,
        color=color,
        title=title,
        barmode=barmode,
        orientation=orientation,
        height=_HEIGHT,
    )
    if width is not None:
        fig.update_traces(width=width)
    fig.update_layout(margin=_MARGIN, legend_title_text="", xaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)


def render_donut_chart(
    df: pd.DataFrame,
    names: str,
    values: str,
    title: str,
) -> None:
    """
    Render a Plotly donut (pie) chart.

    Args:
        df:     Source DataFrame
        names:  Column name for segment labels
        values: Column name for segment sizes
        title:  Chart title
    """
    fig = px.pie(
        df,
        names=names,
        values=values,
        title=title,
        hole=0.45,
        height=_HEIGHT,
    )
    fig.update_layout(margin=_MARGIN)
    st.plotly_chart(fig, use_container_width=True)


def render_heatmap(
    df: pd.DataFrame,
    x: str,
    y: str,
    values: str,
    title: str,
) -> None:
    """
    Render a Plotly heatmap (contributor × date activity matrix).

    Pivots the DataFrame from long format before rendering.

    Args:
        df:     Source DataFrame in long format
        x:      Column for x-axis (e.g. 'activity_date')
        y:      Column for y-axis (e.g. 'username')
        values: Column for cell values (e.g. 'total_activity_count')
        title:  Chart title
    """
    pivot = df.pivot_table(
        index=y,
        columns=x,
        values=values,
        aggfunc="sum",
        fill_value=0,
    )
    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns.astype(str).tolist(),
            y=pivot.index.tolist(),
            colorscale="Blues",
            showscale=True,
        )
    )
    fig.update_layout(
        title=title,
        height=max(_HEIGHT, len(pivot) * 28 + 80),
        margin=_MARGIN,
        xaxis_title="Date",
        yaxis_title="Contributor",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_dual_bar_chart(
    df: pd.DataFrame,
    x: str,
    y1: str,
    y2: str,
    title: str,
    y1_label: str = "",
    y2_label: str = "",
) -> None:
    """
    Render a side-by-side bar chart for two metrics on the same x-axis.

    Used for PR opened vs PR merged comparison.

    Args:
        df:       Source DataFrame
        x:        Column for x-axis (dates)
        y1:       First metric column
        y2:       Second metric column
        title:    Chart title
        y1_label: Display name for y1
        y2_label: Display name for y2
    """
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df[x],
        y=df[y1],
        name=y1_label or y1,
    ))
    fig.add_trace(go.Bar(
        x=df[x],
        y=df[y2],
        name=y2_label or y2,
    ))
    fig.update_layout(
        title=title,
        barmode="group",
        height=_HEIGHT,
        margin=_MARGIN,
        legend_title_text="",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_dataframe_table(
    df: pd.DataFrame,
    title: str = "",
    hide_index: bool = True,
) -> None:
    """
    Render a styled DataFrame table via st.dataframe().

    Args:
        df:         Source DataFrame
        title:      Optional markdown label above the table
        hide_index: Whether to hide the default integer index
    """
    if title:
        st.markdown(f"**{title}**")
    st.dataframe(df, use_container_width=True, hide_index=hide_index)
