"""
Page 1: Overview
=================
Business question: "What is happening overall?"

Layout:
  Title → Description → Filters → KPI Cards → Charts → Table
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timezone
import pandas as pd
import streamlit as st
import services.overview_service as overview_svc
import services.health_service as health_svc
import components.kpi_cards as kpi
import components.charts as charts
import components.sidebar as sidebar


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.title("🏠 Overview")
st.markdown(
    "**Business question:** What is happening overall across the PipeOne platform?"
)
st.markdown(
    "Platform-wide executive summary of GitHub activity ingested across all three "
    "tracked repositories. Every metric is sourced directly from the Gold Layer."
)
st.divider()

# ---------------------------------------------------------------------------
# Filters (sidebar)
# ---------------------------------------------------------------------------
start_date, end_date = sidebar.render_date_range_filter(
    label="Date Range",
    default_days=30,
)

# ---------------------------------------------------------------------------
# KPI Cards
# ---------------------------------------------------------------------------
st.subheader("Platform KPIs (All-Time)")

with st.spinner("Loading KPIs..."):
    platform_kpis = overview_svc.get_platform_kpis()

total_commits   = platform_kpis.get("Total Commits", 0)
commits_in_data = total_commits > 0

# Build the KPI display dict depending on whether commit data is available.
# The GitHub Events API truncates commit arrays for large repos, so
# commit_count may be 0 even for active repositories. In this case,
# push events are shown instead — they are always populated.
if commits_in_data:
    display_kpis = {
        "Total Commits":   f"{total_commits:,}",
        "Push Events":     f"{platform_kpis['Total Pushes']:,}",
        "Total PR Events": f"{platform_kpis['Total PR Events']:,}",
        "Repos Tracked":   platform_kpis["Repos Tracked"],
    }
else:
    display_kpis = {
        "Push Events":     f"{platform_kpis['Total Pushes']:,}",
        "Total PR Events": f"{platform_kpis['Total PR Events']:,}",
        "Repos Tracked":   platform_kpis["Repos Tracked"],
    }

kpi.render_kpi_row(display_kpis)

if not commits_in_data:
    st.info(
        "Commit counts are unavailable because the GitHub Events API truncates commit "
        "payloads for large repositories. Push event counts are displayed instead."
    )

st.divider()

# ---------------------------------------------------------------------------
# Charts — Row 1: Daily activity trend
# ---------------------------------------------------------------------------
st.subheader("Daily Activity Trend")
st.caption(f"Selected Period: {start_date} → {end_date} • All Repositories")

with st.spinner("Loading daily activity..."):
    daily_df = overview_svc.get_daily_activity_all_repos(start_date, end_date)

if daily_df.empty:
    st.info("No activity data found for the selected date range.")
else:
    # Rename technical columns for business-friendly chart labels
    daily_df = daily_df.rename(columns={
        "push_count": "Push Events",
        "pr_event_count": "PR Events",
    })

    # Use commit_count if it has data; fall back to Push Events with a note.
    use_commits     = daily_df["commit_count"].sum() > 0
    activity_col    = "commit_count" if use_commits else "Push Events"
    activity_title  = (
        "Daily Commit Volume (All Repos)"
        if use_commits
        else "Daily Push Volume — All Repos (commit data unavailable)"
    )

    col1, col2 = st.columns(2)
    with col1:
        charts.render_area_chart(
            df=daily_df,
            x="activity_date",
            y=activity_col,
            title=activity_title,
        )
    with col2:
        charts.render_area_chart(
            df=daily_df,
            x="activity_date",
            y="PR Events",
            title="Daily PR Events (All Repos)",
        )

st.divider()

# ---------------------------------------------------------------------------
# Charts — Row 2: Repository comparison + Event distribution
# ---------------------------------------------------------------------------
st.subheader("Repository Comparison")

col3, col4 = st.columns(2)

with col3:
    with st.spinner("Loading repo comparison..."):
        repo_comparison_df = overview_svc.get_repo_comparison()
    if not repo_comparison_df.empty:
        # Rename technical columns for business-friendly chart labels
        repo_comparison_df = repo_comparison_df.rename(columns={
            "total_pushes": "Push Events",
            "total_pr_events": "PR Events",
        })
        # Show pushes vs PR events (always available); commits only if non-zero
        compare_cols = (
            ["total_commits", "PR Events"]
            if repo_comparison_df["total_commits"].sum() > 0
            else ["Push Events", "PR Events"]
        )
        compare_title = (
            "Commits vs PR Events by Repository"
            if repo_comparison_df["total_commits"].sum() > 0
            else "Pushes vs PR Events by Repository"
        )
        charts.render_bar_chart(
            df=repo_comparison_df,
            x="repo_name",
            y=compare_cols,
            title=compare_title,
            barmode="group",
        )

with col4:
    with st.spinner("Loading event distribution..."):
        dist_df = overview_svc.get_event_distribution(start_date, end_date)
    if not dist_df.empty:
        # Rename technical columns for business-friendly chart labels
        dist_df = dist_df.rename(columns={
            "push_count": "Push Events",
            "pr_event_count": "PR Events",
        })
        charts.render_bar_chart(
            df=dist_df,
            x="activity_date",
            y=["Push Events", "PR Events"],
            title="Daily Event Distribution (Pushes vs PRs)",
            barmode="stack",
        )

st.divider()

# ---------------------------------------------------------------------------
# Detailed Table
# ---------------------------------------------------------------------------
st.subheader("Repository Summary Table")
st.caption("All-time cumulative metrics for each tracked repository.")

with st.spinner("Loading repository summary..."):
    repo_table_df = overview_svc.get_repo_comparison()

if not repo_table_df.empty:
    # Show pushes if commits are unavailable
    table_cols = (
        ["repo_name", "total_commits", "total_pushes", "total_pr_events", "stars"]
        if repo_table_df["total_commits"].sum() > 0
        else ["repo_name", "total_pushes", "total_pr_events", "stars"]
    )
    charts.render_dataframe_table(df=repo_table_df[table_cols], title="")

st.divider()

# ---------------------------------------------------------------------------
# Pipeline Lifecycle Status
# ---------------------------------------------------------------------------
st.subheader("Pipeline Lifecycle Status")
st.caption(
    "The freshness badge reflects **Stage 1 — Last Ingested**: "
    "when the GitHub API ingestion script last wrote to the warehouse. "
    "This is the authoritative signal for whether the pipeline ran successfully."
)

with st.spinner("Checking pipeline status..."):
    lifecycle = health_svc.get_pipeline_lifecycle()

# Compute age NOW — outside the cached function so it always uses current time.
now = datetime.now(timezone.utc)

last_ingested      = lifecycle["last_ingested"]        # Stage 1 — fetched_at
data_coverage_date = lifecycle["data_coverage_date"]   # Stage 2 — Latest Available Data
gold_built_at      = lifecycle["gold_built_at"]        # Stage 3 — Gold Layer Refreshed

# Freshness badge is based on Stage 1 (raw ingestion), not Gold created_at.
# This correctly turns GREEN after an Airflow run regardless of the dbt schema.
if last_ingested is not None:
    ingestion_age_hours = round((now - last_ingested).total_seconds() / 3600, 1)
    kpi.render_freshness_badge(ingestion_age_hours)
else:
    st.warning("⚠️ No ingestion records found. Run the Airflow DAG to populate data.")

# Three-column lifecycle display — one column per pipeline stage.
col_a, col_b, col_c = st.columns(3)

with col_a:
    st.markdown("#### 🔵 Stage 1 — Last Ingested")
    st.caption("When the GitHub API script last wrote to `github_events_raw`")
    val = last_ingested.strftime("%Y-%m-%d %H:%M UTC") if last_ingested else "—"
    st.metric(label="Ingestion Timestamp", value=val)

with col_b:
    st.markdown("#### 📅 Stage 2 — Latest Available Data")
    st.caption("Most recent event date present in the Gold Layer")
    st.metric(label="Latest Activity Date", value=data_coverage_date)

with col_c:
    st.markdown("#### ⚙️ Stage 3 — Gold Layer Refreshed")
    st.caption("When dbt last materialised the Gold tables (`created_at`)")
    val = gold_built_at.strftime("%Y-%m-%d %H:%M UTC") if gold_built_at else "—"
    st.metric(label="dbt Build Timestamp", value=val)

st.divider()

# ---------------------------------------------------------------------------
# Community Pulse (Hacker News Teaser)
# ---------------------------------------------------------------------------
st.subheader("🔥 Community Pulse")
st.caption(
    "How are our tracked open-source projects trending in the developer community? "
    "Here is a quick snapshot of Hacker News activity. Sourced from the Gold Layer."
)

import services.hn_service as hn_svc

with st.spinner("Loading Hacker News Pulse..."):
    hn_kpis = hn_svc.get_hn_platform_kpis()
    mention_summary = hn_svc.get_hn_repo_mention_summary()

if hn_kpis and hn_kpis.get("Total HN Stories", 0) > 0:
    col_hn1, col_hn2, col_hn3, col_hn4 = st.columns(4)
    with col_hn1:
        st.metric("HN Stories Ingested", f"{hn_kpis['Total HN Stories']:,}")
    with col_hn2:
        st.metric("Average HN Score", f"{hn_kpis['Average Score']:,}")
    with col_hn3:
        st.metric("Total HN Comments", f"{hn_kpis['Total Comments']:,}")
    with col_hn4:
        st.metric("Unique Community Authors", f"{hn_kpis['Unique Authors']:,}")

    # Small mention summary list/columns
    if not mention_summary.empty:
        st.markdown("#### Repository Mentions on Hacker News (All-Time)")
        m_cols = st.columns(len(mention_summary))
        for idx, row in mention_summary.iterrows():
            with m_cols[idx % len(m_cols)]:
                st.metric(
                    label=row["mentioned_repo"],
                    value=f"{int(row['total_mentions'])} mentions",
                    delta=f"{int(row['total_score'])} upvotes 🌟"
                )
    
    st.page_link("pages/06_Community_Traction.py", label="Explore Full Community Traction", icon="🔥")
else:
    st.info(
        "No Hacker News data found. Run the ingestion pipeline and dbt build to populate Hacker News analytics."
    )


