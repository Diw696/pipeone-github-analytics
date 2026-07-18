"""
Health Service
==============
Data access for the Pipeline Health page.

Business question answered: "Can I trust this data?"

Pipeline lifecycle definitions used throughout this module:

  Stage 1 — Last Ingested  : MAX(fetched_at) from github_events_raw
                             Set by the Python ingestion script when events
                             are written to the warehouse. This is the
                             authoritative signal for "did the pipeline run?"

  Stage 2 — Data Coverage  : MAX(activity_date) from fct_github_daily_activity
                             The most recent calendar date for which GitHub
                             events exist in the warehouse.

  Stage 3 — Gold Built     : MAX(created_at) from Gold tables
                             When dbt last materialised the Gold tables.
                             May differ from Stage 1 if dbt targets a
                             different schema (e.g. dbt_dev vs public).

The freshness badge is based on Stage 1 (fetched_at) — not created_at —
because it correctly reflects a successful ingestion run regardless of
which dbt schema is active.

age_hours is intentionally NOT computed inside cached functions.
It is computed in the calling page with datetime.now(timezone.utc)
so the displayed age is always current, never frozen by the cache.

Author: PipeOne Project
"""

import pandas as pd
import streamlit as st
from services.db import get_connection
from config.settings import CACHE_TTL_SEC

# Freshness queries use a shorter TTL (60 s) so the health page
# reflects a pipeline run within one minute of page reload.
_FRESHNESS_TTL = 60


@st.cache_data(ttl=_FRESHNESS_TTL)
def get_gold_table_stats() -> pd.DataFrame:
    """
    Return row count and last-updated timestamp for each Gold table.

    age_hours is NOT computed here — compute it in the page using
    datetime.now(timezone.utc) so it reflects actual current time,
    not the time the cache was populated.

    Source: All four Gold tables (metadata queries only).

    Returns:
        DataFrame columns: table_name, row_count, last_updated
    """
    conn = get_connection()
    query = """
        SELECT 'dim_repository' AS table_name,
               COUNT(*)        AS row_count,
               MAX(created_at) AS last_updated
        FROM dim_repository

        UNION ALL

        SELECT 'dim_contributor',
               COUNT(*),
               MAX(created_at)
        FROM dim_contributor

        UNION ALL

        SELECT 'fct_github_daily_activity',
               COUNT(*),
               MAX(created_at)
        FROM fct_github_daily_activity

        UNION ALL

        SELECT 'fct_contributor_daily_activity',
               COUNT(*),
               MAX(created_at)
        FROM fct_contributor_daily_activity

        ORDER BY table_name
    """
    df = pd.read_sql(query, conn)
    # Normalise the timestamp column to UTC-aware for safe comparison in pages
    df["last_updated"] = pd.to_datetime(df["last_updated"], utc=True)
    return df


@st.cache_data(ttl=_FRESHNESS_TTL)
def get_pipeline_lifecycle() -> dict:
    """
    Return all three pipeline lifecycle timestamps as a single dict.

    This is the primary freshness function for the Overview page.
    The freshness badge should be derived from `last_ingested` (Stage 1)
    because it reflects the Python ingestion script's last successful run,
    which is independent of the dbt schema target.

    Returns:
        dict with keys:
          last_ingested      (pd.Timestamp UTC-aware, or None)
              Stage 1 — MAX(fetched_at) from github_events_raw
          data_coverage_date (str ISO date, or "Unknown")
              Stage 2 — MAX(activity_date) from fct_github_daily_activity
          gold_built_at      (pd.Timestamp UTC-aware, or None)
              Stage 3 — MAX(created_at) across all Gold tables
    """
    conn = get_connection()

    # Stage 1: ingestion timestamp from the raw table
    ingestion_df = pd.read_sql(
        "SELECT MAX(fetched_at) AS last_ingested FROM github_events_raw",
        conn,
    )

    # Stage 2: most recent event date in the warehouse
    coverage_df = pd.read_sql(
        "SELECT MAX(activity_date) AS data_coverage_date "
        "FROM fct_github_daily_activity",
        conn,
    )

    # Stage 3: when dbt last built the Gold tables
    gold_df = pd.read_sql(
        """
        SELECT MAX(ts) AS gold_built_at
        FROM (
            SELECT MAX(created_at) AS ts FROM dim_repository
            UNION ALL
            SELECT MAX(created_at) FROM dim_contributor
            UNION ALL
            SELECT MAX(created_at) FROM fct_github_daily_activity
            UNION ALL
            SELECT MAX(created_at) FROM fct_contributor_daily_activity
        ) sub
        """,
        conn,
    )

    raw_ingested  = ingestion_df.iloc[0]["last_ingested"]
    raw_coverage  = coverage_df.iloc[0]["data_coverage_date"]
    raw_gold      = gold_df.iloc[0]["gold_built_at"]

    return {
        "last_ingested":      (
            pd.to_datetime(raw_ingested, utc=True)
            if pd.notna(raw_ingested) else None
        ),
        "data_coverage_date": str(raw_coverage) if pd.notna(raw_coverage) else "Unknown",
        "gold_built_at":      (
            pd.to_datetime(raw_gold, utc=True)
            if pd.notna(raw_gold) else None
        ),
    }


@st.cache_data(ttl=_FRESHNESS_TTL)
def get_freshness_summary() -> dict:
    """
    Return a single dict that captures both freshness dimensions.

    Gold Layer Refresh Time  — when dbt last ran (MAX created_at)
    Data Coverage Date       — most recent date with events (MAX last_active_date)

    Both are returned as UTC-aware timestamps / strings so the calling
    page can compare them to datetime.now(timezone.utc) without
    timezone ambiguity.

    Returns:
        dict with keys:
          gold_refresh_time  (pd.Timestamp, UTC-aware, or None)
          data_coverage_date (str ISO date, or "Unknown")
    """
    conn = get_connection()

    # Gold layer refresh: the most recent created_at across all four tables
    refresh_query = """
        SELECT MAX(ts) AS gold_refresh_time
        FROM (
            SELECT MAX(created_at) AS ts FROM dim_repository
            UNION ALL
            SELECT MAX(created_at) FROM dim_contributor
            UNION ALL
            SELECT MAX(created_at) FROM fct_github_daily_activity
            UNION ALL
            SELECT MAX(created_at) FROM fct_contributor_daily_activity
        ) sub
    """
    # Data coverage: the latest activity date in the warehouse
    coverage_query = """
        SELECT MAX(last_active_date) AS data_coverage_date
        FROM dim_repository
    """

    refresh_df  = pd.read_sql(refresh_query, conn)
    coverage_df = pd.read_sql(coverage_query, conn)

    raw_refresh = refresh_df.iloc[0]["gold_refresh_time"]
    raw_coverage = coverage_df.iloc[0]["data_coverage_date"]

    gold_refresh_time = (
        pd.to_datetime(raw_refresh, utc=True) if pd.notna(raw_refresh) else None
    )
    data_coverage_date = str(raw_coverage) if pd.notna(raw_coverage) else "Unknown"

    return {
        "gold_refresh_time":  gold_refresh_time,
        "data_coverage_date": data_coverage_date,
    }


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_data_coverage() -> pd.DataFrame:
    """
    Return date range coverage per repository.

    Source: dim_repository (first_active_date, last_active_date)

    Returns:
        DataFrame columns: repo_name, first_active_date, last_active_date,
                           days_covered
    """
    conn = get_connection()
    query = """
        SELECT
            repo_name,
            first_active_date,
            last_active_date,
            (last_active_date - first_active_date) AS days_covered
        FROM dim_repository
        ORDER BY repo_name
    """
    return pd.read_sql(query, conn)


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_last_ingestion_date() -> str:
    """
    Return the most recent activity_date across all repos.

    Source: fct_github_daily_activity

    Returns:
        ISO date string e.g. '2026-07-15', or 'Unknown'
    """
    conn = get_connection()
    query = "SELECT MAX(activity_date) AS last_date FROM fct_github_daily_activity"
    df = pd.read_sql(query, conn)
    val = df.iloc[0]["last_date"]
    return str(val) if pd.notna(val) else "Unknown"


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_contributor_count() -> int:
    """
    Return the total number of unique contributors tracked.

    Source: dim_contributor

    Returns:
        int: Total distinct contributor count
    """
    conn = get_connection()
    query = "SELECT COUNT(*) AS cnt FROM dim_contributor"
    df = pd.read_sql(query, conn)
    return int(df.iloc[0]["cnt"])


@st.cache_data(ttl=_FRESHNESS_TTL)
def get_hn_gold_table_stats() -> pd.DataFrame:
    """
    Return row count and last-updated timestamp for each Hacker News Gold table.

    Source: dim_hn_story, fct_hn_daily_activity, fct_hn_repo_mentions

    Returns:
        DataFrame columns: table_name, row_count, last_updated
    """
    conn = get_connection()
    query = """
        SELECT 'dim_hn_story'          AS table_name,
               COUNT(*)                AS row_count,
               MAX(created_at)         AS last_updated
        FROM dim_hn_story

        UNION ALL

        SELECT 'fct_hn_daily_activity',
               COUNT(*),
               MAX(created_at)
        FROM fct_hn_daily_activity

        UNION ALL

        SELECT 'fct_hn_repo_mentions',
               COUNT(*),
               MAX(created_at)
        FROM fct_hn_repo_mentions

        ORDER BY table_name
    """
    df = pd.read_sql(query, conn)
    df["last_updated"] = pd.to_datetime(df["last_updated"], utc=True)
    return df


@st.cache_data(ttl=_FRESHNESS_TTL)
def get_hn_pipeline_lifecycle() -> dict:
    """
    Return all three Hacker News pipeline lifecycle timestamps.

    Returns:
        dict with keys:
          last_ingested      (pd.Timestamp UTC-aware, or None)
              Stage 1 — MAX(fetched_at) from hn_stories_raw
          data_coverage_date (str ISO date, or "Unknown")
              Stage 2 — MAX(activity_date) from fct_hn_daily_activity
          gold_built_at      (pd.Timestamp UTC-aware, or None)
              Stage 3 — MAX(created_at) across all HN Gold tables
    """
    conn = get_connection()

    # Stage 1: Ingestion
    ingestion_df = pd.read_sql(
        "SELECT MAX(fetched_at) AS last_ingested FROM hn_stories_raw",
        conn,
    )

    # Stage 2: Coverage
    coverage_df = pd.read_sql(
        "SELECT MAX(activity_date) AS data_coverage_date "
        "FROM fct_hn_daily_activity",
        conn,
    )

    # Stage 3: Gold Build
    gold_df = pd.read_sql(
        """
        SELECT MAX(ts) AS gold_built_at
        FROM (
            SELECT MAX(created_at) AS ts FROM dim_hn_story
            UNION ALL
            SELECT MAX(created_at) FROM fct_hn_daily_activity
            UNION ALL
            SELECT MAX(created_at) FROM fct_hn_repo_mentions
        ) sub
        """,
        conn,
    )

    raw_ingested = ingestion_df.iloc[0]["last_ingested"]
    raw_coverage = coverage_df.iloc[0]["data_coverage_date"]
    raw_gold = gold_df.iloc[0]["gold_built_at"]

    return {
        "last_ingested": (
            pd.to_datetime(raw_ingested, utc=True)
            if pd.notna(raw_ingested) else None
        ),
        "data_coverage_date": str(raw_coverage) if pd.notna(raw_coverage) else "Unknown",
        "gold_built_at": (
            pd.to_datetime(raw_gold, utc=True)
            if pd.notna(raw_gold) else None
        ),
    }


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_hn_data_coverage() -> pd.DataFrame:
    """
    Return date range coverage for Hacker News activity.

    Source: fct_hn_daily_activity

    Returns:
        DataFrame columns: source_name, first_active_date, last_active_date,
                            days_covered
    """
    conn = get_connection()
    query = """
        SELECT
            'Hacker News Top Stories' AS source_name,
            MIN(activity_date) AS first_active_date,
            MAX(activity_date) AS last_active_date,
            (MAX(activity_date) - MIN(activity_date)) AS days_covered
        FROM fct_hn_daily_activity
    """
    return pd.read_sql(query, conn)

