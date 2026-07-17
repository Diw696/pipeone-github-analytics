"""
Page 4: Pipeline Health
========================
Business question: "Can I trust this data?"

Layout:
  Title → Description → (no filters) → KPI Cards → Charts → Table

Freshness definitions used on this page:
  Gold Layer Refresh Time — MAX(created_at) across all Gold tables.
                            Reflects when dbt last ran.
  Data Coverage Date      — MAX(last_active_date) from dim_repository.
                            Reflects the most recent date with events.

age_hours is computed here (outside the cached service calls) so the
displayed age is always accurate, even if the underlying DataFrame
was served from cache.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timezone
import pandas as pd
import streamlit as st
import services.health_service as health_svc
import components.kpi_cards as kpi
import components.charts as charts


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.title("🩺 Pipeline Health")
st.markdown(
    "**Business question:** Can I trust this data?"
)
st.markdown(
    "Operational transparency into the PipeOne data platform. "
    "Before analysing any metric, a data consumer should confirm that "
    "the pipeline is healthy and the Gold Layer tables are up to date."
)
st.divider()

# ---------------------------------------------------------------------------
# Load all health data
# ---------------------------------------------------------------------------
with st.spinner("Loading health metrics..."):
    stats_df          = health_svc.get_gold_table_stats()
    lifecycle         = health_svc.get_pipeline_lifecycle()
    last_ingestion    = health_svc.get_last_ingestion_date()
    contributor_count = health_svc.get_contributor_count()

# Compute age NOW (outside cached functions) so the displayed value
# reflects the current moment, not the time the cache was populated.
now               = datetime.now(timezone.utc)
last_ingested      = lifecycle["last_ingested"]        # Stage 1 — fetched_at
data_coverage     = lifecycle["data_coverage_date"]   # Stage 2 — activity_date
gold_refresh_time = lifecycle["gold_built_at"]        # Stage 3 — created_at

if last_ingested is not None:
    ingestion_age_hours = round((now - last_ingested).total_seconds() / 3600, 1)
else:
    ingestion_age_hours = None

# Also annotate the stats_df with age_hours computed right now.
if not stats_df.empty:
    stats_df["age_hours"] = stats_df["last_updated"].apply(
        lambda ts: round((now - ts).total_seconds() / 3600, 1)
        if pd.notna(ts) else None
    )

# ---------------------------------------------------------------------------
# KPI Cards — top-level health summary
# ---------------------------------------------------------------------------
st.subheader("Platform Health Summary")

# Freshness badge based on raw ingestion age (Stage 1), matching Overview page
if ingestion_age_hours is not None:
    kpi.render_freshness_badge(ingestion_age_hours)
else:
    st.warning("⚠️ No ingestion records found.")

st.divider()

# Two-row KPI strip: freshness first, then platform counts
kpi.render_kpi_row({
    "Last Gold Refresh":  (
        gold_refresh_time.strftime("%Y-%m-%d %H:%M UTC")
        if gold_refresh_time else "Unknown"
    ),
    "Latest Activity Date":    data_coverage,
    "Hours Since Last Ingestion":  ingestion_age_hours if ingestion_age_hours is not None else "Unknown",
})

kpi.render_kpi_row({
    "Gold Tables":          4,
    "Last Activity Date":   last_ingestion,
    "Unique Contributors":  contributor_count,
    "Total Table Rows":     f"{int(stats_df['row_count'].sum()):,}" if not stats_df.empty else "—",
})

st.divider()

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
st.subheader("Gold Layer Metrics")
st.caption(
    "Row counts confirm that each Gold table has been populated. "
    "An empty or unexpectedly low count indicates a pipeline run may have failed."
)

if not stats_df.empty:
    charts.render_bar_chart(
        df=stats_df,
        x="table_name",
        y="row_count",
        title="Row Count per Gold Table",
        barmode="group",
    )

st.divider()

st.subheader("Data Coverage by Repository")
st.caption(
    "Shows the date span captured for each repository. "
    "A short span indicates limited historical data has been ingested."
)

with st.spinner("Loading data coverage..."):
    coverage_df = health_svc.get_data_coverage()

if not coverage_df.empty:
    charts.render_bar_chart(
        df=coverage_df,
        x="repo_name",
        y="days_covered",
        title="Days of Data Covered per Repository",
        barmode="group",
    )

st.divider()

# ---------------------------------------------------------------------------
# Detailed Table — Gold table status
# ---------------------------------------------------------------------------
st.subheader("Gold Tables")
st.caption(
    "Detailed view of each Gold table: row count and dbt run timestamp. "
    "**Gold Layer Refresh Time** is when dbt materialised the table."
)

if not stats_df.empty:
    display_df = stats_df[["table_name", "row_count", "last_updated"]].copy()
    display_df["last_updated"] = display_df["last_updated"].dt.strftime("%Y-%m-%d %H:%M UTC")
    display_df.columns = ["Table", "Row Count", "Last Gold Refresh (UTC)"]
    charts.render_dataframe_table(df=display_df, title="")

st.divider()

st.subheader("Repository Coverage")
st.caption(
    "**Data Coverage Date** is the most recent `last_active_date` across all repos — "
    "this is the latest date for which GitHub events exist in the warehouse. "
    "It is independent of when dbt ran."
)

if not coverage_df.empty:
    display_coverage = coverage_df.copy()
    display_coverage.columns = [
        "Repository", "First Active Date", "Last Active Date", "Days Covered"
    ]
    charts.render_dataframe_table(df=display_coverage, title="")

st.divider()

# ---------------------------------------------------------------------------
# Pipeline architecture reference
# ---------------------------------------------------------------------------
st.subheader("Pipeline Architecture")
st.markdown(
    """
    | Stage | Tool | Description |
    |---|---|---|
    | **Ingestion** | Python + GitHub REST API | Fetches push and PR events per repository |
    | **Storage** | PostgreSQL | Raw events stored in `github_events_raw` |
    | **Bronze** | dbt (staging models) | Selects raw fields with light cleanup |
    | **Silver** | dbt (intermediate models) | Applies business rules, typing, deduplication |
    | **Gold** | dbt (final models) | Dimension and fact tables used by this dashboard |
    | **Orchestration** | Apache Airflow | Schedules ingestion and dbt runs end-to-end |
    | **Analytics** | Streamlit Dashboard | Visualizes verified Gold Layer models. |

    The dashboard never reads from Bronze or Silver. All metrics come from verified, tested Gold tables.
    """
)
