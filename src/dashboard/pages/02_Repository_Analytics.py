"""
Page 2: Repository Analytics
==============================
Business question: "Which repository is performing best?"

Layout:
  Title → Description → Filters → KPI Cards → Charts → Table
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
import services.repository_service as repo_svc
import components.kpi_cards as kpi
import components.charts as charts
import components.sidebar as sidebar


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.title("📂 Repository Analytics")
st.markdown(
    "**Business question:** Which repository is performing best?"
)
st.markdown(
    "Deep dive into individual repository performance. Select a repository "
    "and date range to explore commit trends, PR activity, and push behaviour. "
    "All metrics come from `dim_repository` and `fct_github_daily_activity`."
)
st.divider()

# ---------------------------------------------------------------------------
# Filters (sidebar)
# ---------------------------------------------------------------------------
selected_repo = sidebar.render_repo_filter(include_all=False)
start_date, end_date = sidebar.render_date_range_filter(
    label="Activity Period",
    default_days=30,
)

# ---------------------------------------------------------------------------
# KPI Cards
# ---------------------------------------------------------------------------
st.subheader(f"Repository KPIs — {selected_repo}")

with st.spinner("Loading repository KPIs..."):
    repo_kpis = repo_svc.get_repo_kpis(selected_repo)

if repo_kpis:
    # Check if commit metrics are available (greater than 0)
    commits_available = repo_kpis.get("Total Commits", 0) > 0

    # Build KPI dict conditionally
    kpi_dict = {
        "Language":         repo_kpis["Language"],
        "Stars":            repo_kpis["Stars"],
    }
    if commits_available:
        kpi_dict["Total Commits"] = f"{repo_kpis['Total Commits']:,}"
    kpi_dict["Total Pushes"] = f"{repo_kpis['Total Pushes']:,}"
    kpi_dict["Total PR Events"] = f"{repo_kpis['Total PR Events']:,}"

    # Render KPI cards
    kpi.render_kpi_row(kpi_dict)

    st.caption(
        f"Owner: **{repo_kpis['Owner']}** | "
        f"Active: {repo_kpis['First Active']} → {repo_kpis['Last Active']}"
    )

    if not commits_available:
        st.info(
            "ℹ️ **Commit count is not available for this repository.** "
            "The GitHub Events API truncates commit payloads for large, high-volume "
            "repositories. Push event counts are shown instead."
        )
else:
    st.warning(f"No data found for repository: {selected_repo}")
    commits_available = False

st.divider()

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
with st.spinner("Loading daily activity..."):
    daily_df = repo_svc.get_repo_daily_activity(selected_repo, start_date, end_date)

if daily_df.empty:
    st.info("No activity data found for the selected repository and date range.")
else:
    # Row 1: Push Activity
    st.subheader("Push Activity")
    st.caption(f"Period: {start_date} → {end_date}")

    col1, col2 = st.columns(2)
    with col1:
        charts.render_area_chart(
            df=daily_df,
            x="activity_date",
            y="push_count",
            title="Daily Push Events",
        )
    with col2:
        charts.render_line_chart(
            df=daily_df,
            x="activity_date",
            y="total_activity_count",
            title="Daily Total Activity Volume",
        )

    st.divider()

    # Row 2: PR activity
    st.subheader("Pull Request Activity")
    st.caption(
        "PR merge rate (`pr_merged_pct`) is pre-computed in the Gold Layer by dbt. "
        "It is not recalculated here."
    )

    col3, col4 = st.columns(2)
    with col3:
        charts.render_dual_bar_chart(
            df=daily_df,
            x="activity_date",
            y1="pr_opened",
            y2="pr_merged",
            title="PRs Opened vs Merged per Day",
            y1_label="PRs Opened",
            y2_label="PRs Merged",
        )
    with col4:
        # Only plot pr_merged_pct where it is not null (push-only days are null by design)
        pct_df = daily_df.dropna(subset=["pr_merged_pct"])
        if pct_df.empty:
            st.info("No PR merge rate data available for this period.")
        else:
            charts.render_line_chart(
                df=pct_df,
                x="activity_date",
                y="pr_merged_pct",
                title="PR Merge Rate % (pr_merged_pct)",
                y_label="Merge Rate (%)",
            )

st.divider()

# ---------------------------------------------------------------------------
# Detailed Table
# ---------------------------------------------------------------------------
st.subheader("All-Repository Comparison (Selected Period)")
st.caption(
    "Aggregated metrics for all repositories over the selected date range. "
    "Use this to benchmark the selected repository against peers."
)

with st.spinner("Loading comparison table..."):
    summary_df = repo_svc.get_repo_summary_table(start_date, end_date)

if not summary_df.empty:
    # Remove total_commits if they are not available
    if not commits_available:
        summary_df = summary_df.drop(columns=["total_commits"], errors="ignore")
    charts.render_dataframe_table(
        df=summary_df,
        title="",
    )

