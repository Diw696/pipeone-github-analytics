"""
Page 6: Community Traction
===========================
Business question: "How are our tracked projects trending in the developer community?"

Layout:
  Title → Description → Filters → KPI Cards → Repository Mentions → Trends → Lists
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
import services.hn_service as hn_svc
import components.kpi_cards as kpi
import components.charts as charts
import components.sidebar as sidebar


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.title("🔥 Community Traction")
st.markdown(
    "**Business question:** How are our tracked projects trending in the developer community?"
)
st.markdown(
    "Analyze Hacker News community discussions, upvotes, and mentions of "
    "our monitored open-source repositories. Every metric is sourced from the Gold Layer."
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
st.subheader("Community Overview (All-Time)")

with st.spinner("Loading community KPIs..."):
    hn_kpis = hn_svc.get_hn_platform_kpis()

if hn_kpis and hn_kpis.get("Total HN Stories", 0) > 0:
    kpi.render_kpi_row({
        "HN Stories Ingested": f"{hn_kpis['Total HN Stories']:,}",
        "Average Story Score": f"{hn_kpis['Average Score']:,}",
        "Total Comments":       f"{hn_kpis['Total Comments']:,}",
        "Unique Authors":       f"{hn_kpis['Unique Authors']:,}",
    })
else:
    st.warning("No Hacker News data found. Make sure the ingestion pipeline has run.")
    st.stop()

st.divider()

# ---------------------------------------------------------------------------
# Repository Mentions Analysis
# ---------------------------------------------------------------------------
st.subheader("Repository Traction in the Community")
st.caption("Mentions and upvotes accumulated on Hacker News stories.")

with st.spinner("Loading mention summary..."):
    mention_summary = hn_svc.get_hn_repo_mention_summary(start_date, end_date)

if mention_summary.empty:
    st.info("No repository mentions found on Hacker News for the selected date range.")
else:
    col1, col2 = st.columns(2)
    with col1:
        # Render horizontal bar chart of mention count
        charts.render_bar_chart(
            df=mention_summary,
            x="mentioned_repo",
            y="total_mentions",
            title="Total Mentions on Hacker News",
            color="mentioned_repo"
        )
    with col2:
        # Render horizontal bar chart of community upvotes
        charts.render_bar_chart(
            df=mention_summary,
            x="mentioned_repo",
            y="total_score",
            title="Total Community Upvotes (Score)",
            color="mentioned_repo"
        )

st.divider()

# ---------------------------------------------------------------------------
# Daily Activity Trends
# ---------------------------------------------------------------------------
st.subheader("Community Activity Trends")
st.caption(f"Selected Period: {start_date} → {end_date}")

with st.spinner("Loading activity trends..."):
    daily_df = hn_svc.get_hn_daily_activity(start_date, end_date)

if daily_df.empty:
    st.info("No community activity data found for the selected date range.")
else:
    col3, col4 = st.columns(2)
    with col3:
        charts.render_area_chart(
            df=daily_df,
            x="activity_date",
            y="story_count",
            title="Daily HN Stories Ingested",
        )
    with col4:
        charts.render_area_chart(
            df=daily_df,
            x="activity_date",
            y="total_comments",
            title="Daily Community Engagement (Comments)",
        )

st.divider()

# ---------------------------------------------------------------------------
# Leaderboards & Story Highlights
# ---------------------------------------------------------------------------
st.subheader("Community Highlights")

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("#### Top Prolific Authors")
    st.caption("Active community members submitting top stories.")
    with st.spinner("Loading top authors..."):
        top_authors = hn_svc.get_hn_top_authors(limit=5)
    if not top_authors.empty:
        display_authors = top_authors.rename(columns={
            "author": "Author",
            "story_count": "Stories",
            "total_score": "Total Score"
        })
        charts.render_dataframe_table(df=display_authors)
    else:
        st.info("No author information available.")

with col_b:
    st.markdown("#### Trending Hacker News Stories")
    st.caption("Stories receiving the highest score (upvotes) all-time.")
    with st.spinner("Loading trending stories..."):
        trending_stories = hn_svc.get_hn_trending_stories(limit=5)
    if not trending_stories.empty:
        display_trending = trending_stories.rename(columns={
            "title": "Title",
            "score": "Score",
            "comment_count": "Comments",
            "url": "Link"
        })
        charts.render_dataframe_table(df=display_trending[["Title", "Score", "Comments", "Link"]])
    else:
        st.info("No trending stories available.")

st.divider()

# ---------------------------------------------------------------------------
# Recent Headlines Table
# ---------------------------------------------------------------------------
st.subheader("Recent Community Headlines")
st.caption("Latest Hacker News stories ingested by the platform.")

with st.spinner("Loading recent headlines..."):
    recent_stories = hn_svc.get_hn_recent_stories(limit=10)

if not recent_stories.empty:
    display_recent = recent_stories.rename(columns={
        "title": "Title",
        "author": "Author",
        "score": "Score",
        "comment_count": "Comments",
        "published_at": "Published At",
        "url": "Link"
    })
    charts.render_dataframe_table(df=display_recent[["Title", "Author", "Score", "Comments", "Published At", "Link"]])
else:
    st.info("No recent headlines available.")
