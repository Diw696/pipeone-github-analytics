"""
Page 3: Contributor Analytics
==============================
Business question: "Who is contributing the most?"

Layout:
  Title → Description → Filters → KPI Cards → Charts → Table
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
    "Analyze contributor activity across repositories. "
    "All metrics are sourced from the Gold Layer."
)
st.divider()

# ---------------------------------------------------------------------------
# Filters (sidebar)
# ---------------------------------------------------------------------------
selected_repo = sidebar.render_repo_filter(include_all=True)
contrib_type  = sidebar.render_contrib_type_filter()
start_date, end_date = sidebar.render_date_range_filter(
    label="Date Range",
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
with st.spinner("Loading contributor data..."):
    leaderboard_df = contrib_svc.get_contributor_leaderboard(repo_filter, contrib_type)

total_contributors = len(leaderboard_df)
if total_contributors > 0:
    top_contributor = leaderboard_df.iloc[0]["username"]
    avg_activity = round(leaderboard_df["total_activity"].mean(), 1)
else:
    top_contributor = "—"
    avg_activity = 0.0

kpi.render_kpi_row({
    "Total Contributors":             total_contributors,
    "Top Contributor":                top_contributor,
    "Average Activity / Contributor": avg_activity,
})

st.divider()

# --- Top Contributors Chart ---
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

# --- Full Leaderboard Table ---
st.subheader("Full Leaderboard")
st.caption("Ranked by total activity across the selected filters.")

if not leaderboard_df.empty:
    # Rename columns for business-friendly presentation
    display_df = leaderboard_df.rename(columns={
        "rank":               "Rank",
        "username":           "Contributor",
        "contrib_type":       "Type",
        "total_activity":     "Total Activity",
        "total_push_events":  "Push Events",
        "total_pr_events":    "PR Events",
    })

    # Drop columns where every visible value is zero — they add no signal
    zero_cols = [c for c in ["Push Events", "PR Events"] if display_df[c].sum() == 0]
    display_df = display_df.drop(columns=zero_cols)

    # Replace "unknown" contributor type with a readable label
    if "Type" in display_df.columns:
        display_df["Type"] = display_df["Type"].replace("unknown", "Unclassified")

    charts.render_dataframe_table(df=display_df, title="")
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

# Default to highest-ranked contributor for the active filters
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

# ---------------------------------------------------------------------------
# Load all data for the selected contributor up front
# ---------------------------------------------------------------------------
with st.spinner(f"Loading profile for {selected_contributor}..."):
    profile          = contrib_svc.get_contributor_profile(selected_contributor)
    participation_df = contrib_svc.get_contributor_repo_participation(selected_contributor)
    timeline_df      = contrib_svc.get_contributor_timeline(
        selected_contributor, start_date, end_date
    )

if not profile:
    st.warning(f"No data found for **{selected_contributor}**.")
    st.stop()

# ---------------------------------------------------------------------------
# Derived metrics
# ---------------------------------------------------------------------------
total_pushes    = profile["Total Pushes"]
total_pr_events = profile["Total PR Events"]
repos_count     = len(participation_df) if not participation_df.empty else 1
active_days     = timeline_df["activity_date"].nunique() if not timeline_df.empty else 0
total_pr_merged = int(participation_df["pr_merged"].sum()) if not participation_df.empty else 0
first_active    = profile["First Active"]
last_active     = profile["Last Active"]

# ---------------------------------------------------------------------------
# Contributor Summary — two-row compact metric grid
# ---------------------------------------------------------------------------
st.markdown(f"#### {selected_contributor}")

# Row 1 — activity totals
r1c1, r1c2, r1c3 = st.columns(3)
r1c1.metric("Push Events",  f"{total_pushes:,}")
r1c2.metric("PR Events",    f"{total_pr_events:,}")
r1c3.metric("Merged PRs",   f"{total_pr_merged:,}")

# Row 2 — engagement context
r2c1, r2c2, r2c3 = st.columns(3)
r2c1.metric("Repositories", repos_count)
r2c2.metric("Active Days",  active_days)
r2c3.metric("First → Latest Activity", f"{first_active} → {last_active}")

st.divider()

# ---------------------------------------------------------------------------
# Repository Breakdown — compact summary (no chart)
# ---------------------------------------------------------------------------
if not participation_df.empty:
    st.subheader("Repository Breakdown")
    st.caption(f"All-time contribution split for **{selected_contributor}**.")

    if len(participation_df) == 1:
        # Single repo — plain text summary, no chart needed
        row = participation_df.iloc[0]
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Repository",   row["repo_name"])
        col_b.metric("Push Events",  int(row["total_pushes"]))
        col_c.metric("PR Events",    int(row["total_pr_events"]))
    else:
        # Multiple repos — compact summary table
        repo_display = participation_df.rename(columns={
            "repo_name":       "Repository",
            "total_pushes":    "Push Events",
            "total_pr_events": "PR Events",
            "pr_merged":       "Merged PRs",
        })[["Repository", "Push Events", "PR Events", "Merged PRs"]].copy()

        # Drop columns where every value is zero — they add no signal
        zero_cols = [c for c in ["PR Events", "Merged PRs"] if repo_display[c].sum() == 0]
        repo_display = repo_display.drop(columns=zero_cols)

        charts.render_dataframe_table(df=repo_display, title="")

