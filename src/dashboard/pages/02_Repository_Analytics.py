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
    "Analyze push and pull request activity for a selected repository. "
    "All metrics are sourced from the Gold Layer."
)
st.divider()

# ---------------------------------------------------------------------------
# Filters (sidebar)
# ---------------------------------------------------------------------------
selected_repo = sidebar.render_repo_filter(include_all=False)
start_date, end_date = sidebar.render_date_range_filter(
    label="Date Range",
    default_days=30,
)

# ---------------------------------------------------------------------------
# KPI Cards
# ---------------------------------------------------------------------------
st.subheader(f"Repository Overview — {selected_repo}")

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
        f"Data Coverage: {repo_kpis['First Active']} → {repo_kpis['Last Active']}"
    )

    if not commits_available:
        st.info(
            "Commit counts are unavailable because the GitHub Events API truncates "
            "commit payloads. Push events are shown instead."
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
            title="Daily Repository Activity",
        )

    st.divider()

    # Row 2: PR activity
    st.subheader("Pull Request Activity")
    st.caption(
        "PR merge rate is pre-computed in the Gold Layer. is pre-computed in the Gold Layer by dbt. "
        "It is not recalculated here."
    )

    col3, col4 = st.columns(2)
    with col3:
        charts.render_dual_bar_chart(
            df=daily_df,
            x="activity_date",
            y1="pr_opened",
            y2="pr_merged",
            title="Daily PR Activity",
            y1_label="PRs Opened",
            y2_label="PRs Merged",
        )
    with col4:
        st.markdown("#### PR Performance Summary")
        st.caption("Aggregate metrics over the selected period.")
        
        # Add spacing to vertically align with the adjacent chart
        st.write("")
        st.write("")
        
        total_opened = int(daily_df["pr_opened"].sum())
        total_merged = int(daily_df["pr_merged"].sum())
        merge_rate = (total_merged / total_opened * 100) if total_opened > 0 else 0.0
        
        sub_col1, sub_col2, sub_col3 = st.columns(3)
        with sub_col1:
            st.metric(label="PR Merge Rate", value=f"{merge_rate:.1f}%")
        with sub_col2:
            st.metric(label="Merged PRs", value=f"{total_merged:,}")
        with sub_col3:
            st.metric(label="Opened PRs", value=f"{total_opened:,}")

import services.hn_service as hn_svc

st.divider()

# ---------------------------------------------------------------------------
# Community Mentions (Hacker News)
# ---------------------------------------------------------------------------
st.subheader("🔥 Hacker News Community Mentions")
st.caption(
    f"Tracked mentions and traction for **{selected_repo}** on Hacker News. "
    f"Sourced from the Gold and Silver Layers."
)

with st.spinner("Loading Hacker News community mentions..."):
    # Fetch mentions over time
    hn_trends_df = hn_svc.get_hn_repo_mentions_over_time(selected_repo, start_date, end_date)
    # Fetch recent HN stories
    hn_stories_df = hn_svc.get_hn_repo_stories(selected_repo, limit=5)

if not hn_trends_df.empty:
    total_hn_mentions = int(hn_trends_df["mention_count"].sum())
    total_hn_score = int(hn_trends_df["total_score"].sum())
    total_hn_comments = int(hn_trends_df["total_comments"].sum())
    
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("Total HN Mentions", f"{total_hn_mentions:,}")
    with col_m2:
        st.metric("Total HN Upvotes (Score)", f"{total_hn_score:,}")
    with col_m3:
        st.metric("Total HN Comments", f"{total_hn_comments:,}")

    # Only render trend chart when there are at least 4 historical data points
    # (more than 3 aggregated time buckets) to communicate an actual trend.
    if len(hn_trends_df) >= 4:
        st.markdown("#### Mention Trend Over Time")
        charts.render_area_chart(
            df=hn_trends_df,
            x="activity_date",
            y="mention_count",
            title=f"Daily Hacker News Mentions — {selected_repo}",
        )
else:
    st.info("No Hacker News mentions found for this repository during the selected date range.")

if not hn_stories_df.empty:
    st.markdown(f"#### Recent Hacker News Stories mentioning {selected_repo}")
    # format display table
    display_stories = hn_stories_df.rename(columns={
        "title": "Title",
        "author": "Author",
        "score": "Score",
        "comment_count": "Comments",
        "published_at": "Published At",
        "url": "Link"
    })
    charts.render_dataframe_table(df=display_stories[["Title", "Author", "Score", "Comments", "Published At", "Link"]])
else:
    st.caption("No stories mentioning this repository found recently.")

st.divider()

# ---------------------------------------------------------------------------
# Detailed Table
# ---------------------------------------------------------------------------
st.subheader("Repository Comparison")
st.caption(
    "Compare the selected repository with the other tracked repositories over the selected period."
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

