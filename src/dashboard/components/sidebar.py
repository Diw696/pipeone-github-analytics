"""
Sidebar Component
=================
Renders filter controls in the Streamlit sidebar.

Returns structured filter values to the calling page.
The sidebar component never calls services or reads from the database.

Author: PipeOne Project
"""

from datetime import date, timedelta
import streamlit as st
from config.settings import REPOS


def render_date_range_filter(
    label: str = "Date Range",
    default_days: int = 30,
) -> tuple[date, date]:
    """
    Render a date range picker in the sidebar.

    Defaults to the last 30 days.

    Args:
        label:        Section label displayed above the filter
        default_days: Number of days to look back for the default range

    Returns:
        tuple: (start_date, end_date) as Python date objects
    """
    st.sidebar.subheader(label)
    default_end   = date.today()
    default_start = default_end - timedelta(days=default_days)

    start_date = st.sidebar.date_input("Start date", value=default_start)
    end_date   = st.sidebar.date_input("End date",   value=default_end)

    if start_date > end_date:
        st.sidebar.error("Start date must be before end date.")

    return start_date, end_date


def render_repo_filter(include_all: bool = True) -> str:
    """
    Render a repository selector in the sidebar.

    Args:
        include_all: If True, adds an "All Repositories" option at the top.

    Returns:
        Selected repo name string, or "All" if the all-option is chosen.
    """
    st.sidebar.subheader("Repository")
    options = (["All Repositories"] + REPOS) if include_all else REPOS
    selection = st.sidebar.selectbox("Select repository", options=options)
    # Normalise "All Repositories" → "All" for service layer
    return "All" if selection == "All Repositories" else selection


def render_contrib_type_filter() -> str:
    """
    Render a contributor-type filter in the sidebar.

    Maps to the contrib_type field in dim_contributor.
    Values: push_only | pr_only | both | unknown

    Returns:
        Selected type string, or "All" for no filter.
    """
    st.sidebar.subheader("Contributor Type")
    options = ["All", "push_only", "pr_only", "both"]
    return st.sidebar.selectbox("Filter by type", options=options)
