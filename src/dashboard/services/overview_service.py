"""
Overview Service
================
Data access for the Overview page.

Business question answered: "What is happening overall?"

All metrics are read directly from the Gold Layer.
No calculations are performed here — all derived fields
(pr_merged_pct, total_activity_count) come pre-computed from dbt.

Author: PipeOne Project
"""

import pandas as pd
import streamlit as st
from services.db import get_connection
from config.settings import CACHE_TTL_SEC


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_platform_kpis() -> dict:
    """
    Return platform-wide KPI totals across all repos and all time.

    Source: dim_repository (pre-aggregated totals from dbt Gold)

    Returns:
        dict with keys: total_commits, total_pushes, total_pr_events,
                        total_pr_merged, repo_count
    """
    conn = get_connection()
    query = """
        SELECT
            SUM(total_commits)      AS total_commits,
            SUM(total_pushes)       AS total_pushes,
            SUM(total_pr_events)    AS total_pr_events,
            COUNT(repo_name)        AS repo_count
        FROM dim_repository
    """
    df = pd.read_sql(query, conn)
    row = df.iloc[0]
    return {
        "Total Commits":    int(row["total_commits"] or 0),
        "Total Pushes":     int(row["total_pushes"] or 0),
        "Total PR Events":  int(row["total_pr_events"] or 0),
        "Repos Tracked":    int(row["repo_count"] or 0),
    }


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_daily_activity_all_repos(start_date, end_date) -> pd.DataFrame:
    """
    Return daily commit and PR event totals, aggregated across all repos.

    Source: fct_github_daily_activity

    Args:
        start_date: Filter start (date or str)
        end_date:   Filter end (date or str)

    Returns:
        DataFrame columns: activity_date, commit_count, pr_event_count,
                           push_count, total_activity_count
    """
    conn = get_connection()
    query = """
        SELECT
            activity_date,
            SUM(commit_count)           AS commit_count,
            SUM(pr_event_count)         AS pr_event_count,
            SUM(push_count)             AS push_count,
            SUM(total_activity_count)   AS total_activity_count
        FROM fct_github_daily_activity
        WHERE activity_date BETWEEN %s AND %s
        GROUP BY activity_date
        ORDER BY activity_date
    """
    return pd.read_sql(query, conn, params=[start_date, end_date])


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_repo_comparison() -> pd.DataFrame:
    """
    Return per-repository summary for comparison bar chart.

    Source: dim_repository (all-time cumulative metrics from dbt Gold)

    Returns:
        DataFrame columns: repo_name, total_commits, total_pushes,
                           total_pr_events, stars
    """
    conn = get_connection()
    query = """
        SELECT
            repo_name,
            total_commits,
            total_pushes,
            total_pr_events,
            stars
        FROM dim_repository
        ORDER BY total_commits DESC
    """
    return pd.read_sql(query, conn)


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_event_distribution(start_date, end_date) -> pd.DataFrame:
    """
    Return daily push-count vs PR-event-count for the platform.

    Used to render the event-type distribution stacked bar chart.
    Source: fct_github_daily_activity

    Args:
        start_date: Filter start
        end_date:   Filter end

    Returns:
        DataFrame columns: activity_date, push_count, pr_event_count
    """
    conn = get_connection()
    query = """
        SELECT
            activity_date,
            SUM(push_count)       AS push_count,
            SUM(pr_event_count)   AS pr_event_count
        FROM fct_github_daily_activity
        WHERE activity_date BETWEEN %s AND %s
        GROUP BY activity_date
        ORDER BY activity_date
    """
    return pd.read_sql(query, conn, params=[start_date, end_date])


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_data_freshness() -> pd.DataFrame:
    """
    Return the most recent created_at timestamp from each Gold table.

    Source: All four Gold tables (metadata query only)

    Returns:
        DataFrame columns: table_name, last_updated
    """
    conn = get_connection()
    query = """
        SELECT 'dim_repository'               AS table_name,
               MAX(created_at)                AS last_updated
        FROM dim_repository
        UNION ALL
        SELECT 'dim_contributor',             MAX(created_at)
        FROM dim_contributor
        UNION ALL
        SELECT 'fct_github_daily_activity',   MAX(created_at)
        FROM fct_github_daily_activity
        UNION ALL
        SELECT 'fct_contributor_daily_activity', MAX(created_at)
        FROM fct_contributor_daily_activity
        ORDER BY last_updated DESC
    """
    return pd.read_sql(query, conn)
