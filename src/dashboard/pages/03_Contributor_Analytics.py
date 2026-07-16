"""
Page 3: Contributor Analytics
==============================
Business question: "Who is contributing the most?"

Layout:
  Title → Description → Filters → KPI Cards → Charts → Table

Split into two sections on one page:
  TOP:    Platform-level leaderboard and rankings
  BOTTOM: Individual contributor profile and timeline
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
import services.contributor_service as contrib_svc
import components.kpi_cards as kpi
import components.charts as charts
import components.sidebar as sidebar


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.title("👤 Contributor Analytics")
st.markdown(
    "**Business question:** Who is contributing the most?"
)
st.markdown(
    "Explore contributor performance across repositories. The top section shows "
    "platform-wide rankings and total activity. The bottom section "
    "provides a detailed profile for any individual contributor. "
    "All data sourced from `dim_contributor` and `fct_contributor_daily_activity`."
)
st.divider()

# ---------------------------------------------------------------------------
# Filters (sidebar)
# ---------------------------------------------------------------------------
selected_repo    = sidebar.render_repo_filter(include_all=True)
contrib_type     = sidebar.render_contrib_type_filter()
start_date, end_date = sidebar.render_date_range_filter(
    label="Profile Date Range",
    default_days=30,
)

# Normalise "All" to None for service calls where needed
repo_filter = selected_repo  # services accept "All" directly

# ===========================================================================
# SECTION A — Platform-Level Leaderboard
# ===========================================================================
st.subheader("Platform Overview")
st.caption(
    f"Repository: **{selected_repo}** | "
    f"Contributor Type: **{contrib_type}**"
)

# --- KPI Cards (platform-wide totals) ---
with st.spinner("Loading contributor counts..."):
    leaderboard_df = contrib_svc.get_contributor_leaderboard(repo_filter, contrib_type)

total_contributors = len(leaderboard_df)
if total_contributors > 0:
    top_contributor = leaderboard_df.iloc[0]["username"]
    avg_activity = round(leaderboard_df["total_activity"].mean(), 1)
else:
    top_contributor = "None"
    avg_activity = 0.0

kpi.render_kpi_row({
    "Total Contributors":             total_contributors,
    "Top Contributor":                top_contributor,
    "Average Activity / Contributor": avg_activity,
})

st.divider()

# --- Charts: Leaderboard ---
st.subheader("Contributor Rankings")

with st.spinner("Loading top contributors..."):
    top_df = contrib_svc.get_top_by_total_activity(repo_filter, top_n=10)
if not top_df.empty:
    charts.render_bar_chart(
        df=top_df,
        x="total_activity_count",
        y="username",
        title="Top 10 Contributors by Total Activity",
        orientation="h",
    )
else:
    st.info("No activity data available.")

st.divider()

# --- Detailed Leaderboard Table ---
st.subheader("Full Leaderboard")
st.caption(
    "Ranked by total activity. "
    "`contrib_type` is pre-classified by dbt in `dim_contributor`."
)

if not leaderboard_df.empty:
    charts.render_dataframe_table(df=leaderboard_df, title="")
else:
    st.info("No contributors found for the selected filters.")

st.divider()

# ===========================================================================
# SECTION B — Individual Contributor Profile
# ===========================================================================
st.subheader("Individual Contributor Profile")
st.caption("Select a contributor to view their personal activity breakdown.")

with st.spinner("Loading contributor list..."):
    contributor_list = contrib_svc.get_contributor_list()

if not contributor_list:
    st.warning("No contributors found in the database.")
    st.stop()

# Determine default selected contributor (highest-ranked contributor for currently selected filters)
default_index = 0
if not leaderboard_df.empty and contributor_list:
    top_contrib = leaderboard_df.iloc[0]["username"]
    if top_contrib in contributor_list:
        default_index = contributor_list.index(top_contrib)

selected_contributor = st.selectbox(
    label="Select contributor",
    options=contributor_list,
    index=default_index,
    key="contributor_selector",
)

st.divider()

# --- Profile KPI Cards ---
with st.spinner(f"Loading profile for {selected_contributor}..."):
    profile = contrib_svc.get_contributor_profile(selected_contributor)

if profile:
    kpi.render_kpi_row({
        "Contributor Type": profile["Contributor Type"],
        "Total Pushes":     f"{profile['Total Pushes']:,}",
        "Total PR Events":  f"{profile['Total PR Events']:,}",
    })
    st.caption(
        f"Active: **{profile['First Active']}** → **{profile['Last Active']}**"
    )

st.divider()

# --- Individual Charts ---
st.subheader(f"Activity Timeline — {selected_contributor}")
st.caption(f"Period: {start_date} → {end_date}")

with st.spinner("Loading activity timeline..."):
    timeline_df = contrib_svc.get_contributor_timeline(
        selected_contributor, start_date, end_date
    )

if timeline_df.empty:
    st.info(
        f"No activity data for **{selected_contributor}** "
        f"in the selected date range."
    )
else:
    col3, col4 = st.columns(2)
    with col3:
        charts.render_area_chart(
            df=timeline_df,
            x="activity_date",
            y="push_count",
            color="repo_name",
            title="Daily Push Events by Repository",
            color_label="Repository",
        )
    with col4:
        charts.render_bar_chart(
            df=timeline_df,
            x="activity_date",
            y="pr_event_count",
            color="repo_name",
            title="Daily PR Events by Repository",
            barmode="stack",
        )

    # PR Merge rate trend (only where non-null — push-only days have null by design)
    pct_df = timeline_df.dropna(subset=["pr_merged_pct"])
    if not pct_df.empty:
        charts.render_line_chart(
            df=pct_df,
            x="activity_date",
            y="pr_merged_pct",
            color="repo_name",
            title="PR Merge Rate % Over Time",
            color_label="Repository",
        )

st.divider()

# --- Repository Participation Table ---
st.subheader("Repository Participation")
st.caption(
    f"All-time contribution breakdown for **{selected_contributor}** by repository."
)

with st.spinner("Loading repository participation..."):
    participation_df = contrib_svc.get_contributor_repo_participation(selected_contributor)

if not participation_df.empty:
    charts.render_dataframe_table(df=participation_df, title="")
else:
    st.info("No repository participation data available.")
