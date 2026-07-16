"""
KPI Cards Component
===================
Renders KPI metric strips and status badges.

Rules:
  - No database calls in this module.
  - Accepts only scalars and dicts.
  - All formatting logic is here; no formatting in pages.

Author: PipeOne Project
"""

import streamlit as st


def render_kpi_row(metrics: dict) -> None:
    """
    Render a horizontal row of st.metric() cards.

    Args:
        metrics: dict mapping label (str) to value (any).
                 Value is displayed as-is. Format before passing in.

    Example:
        render_kpi_row({
            "Total Commits": "12,450",
            "Repos Tracked": 3,
            "Total PR Events": "8,200",
        })
    """
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics.items()):
        col.metric(label=label, value=value)


def render_freshness_badge(age_hours: float) -> None:
    """
    Render a data freshness status banner.

    Green  → data updated within 24 hours (fresh)
    Yellow → data is 1–2 days old (stale warning)
    Red    → data is older than 2 days (stale error)

    Args:
        age_hours: Hours since last Gold table update.
                   Pass None to render an "unknown" warning.
    """
    if age_hours is None:
        st.warning("⚠️ Data freshness could not be determined.")
        return

    if age_hours <= 24:
        st.success(f"✅ Data is fresh — last updated {age_hours:.1f} hours ago.")
    elif age_hours <= 48:
        st.warning(f"⚠️ Data is {age_hours:.1f} hours old. Pipeline may need attention.")
    else:
        st.error(f"❌ Data is {age_hours:.1f} hours old. Pipeline has not run recently.")
