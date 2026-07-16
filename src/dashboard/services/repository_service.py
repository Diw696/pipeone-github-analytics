"""
Repository Service
==================
Data access for the Repository Analytics page.

Business question answered: "Which repository is performing best?"

All metrics read from Gold Layer.
pr_merged_pct, push_avg_commits — pre-computed by dbt, never recalculated here.

Author: PipeOne Project
"""

import pandas as pd
import streamlit as st
from services.db import get_connection
from config.settings import CACHE_TTL_SEC


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_repository_list() -> list[str]:
    """
    Return all tracked repository names in alphabetical order.

    Source: dim_repository

    Returns:
        List of repo name strings e.g. ['facebook/react', ...]
    """
    conn = get_connection()
    query = "SELECT repo_name FROM dim_repository ORDER BY repo_name"
    df = pd.read_sql(query, conn)
    return df["repo_name"].tolist()


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_repo_kpis(repo_name: str) -> dict:
    """
    Return all-time KPI metrics for a single repository.

    Source: dim_repository (pre-aggregated in dbt Gold)

    Args:
        repo_name: Repository identifier e.g. 'facebook/react'

    Returns:
        dict with keys: repo_name, owner, language, stars, total_pushes,
                        total_commits, total_pr_events,
                        first_active_date, last_active_date
    """
    conn = get_connection()
    query = """
        SELECT
            repo_name,
            owner,
            language,
            stars,
            total_pushes,
            total_commits,
            total_pr_events,
            first_active_date,
            last_active_date
        FROM dim_repository
        WHERE repo_name = %s
    """
    df = pd.read_sql(query, conn, params=[repo_name])
    if df.empty:
        return {}
    row = df.iloc[0]
    return {
        "Repository":       row["repo_name"],
        "Owner":            row["owner"],
        "Language":         row["language"],
        "Stars":            f"{int(row['stars'] or 0):,}",
        "Total Pushes":     int(row["total_pushes"] or 0),
        "Total Commits":    int(row["total_commits"] or 0),
        "Total PR Events":  int(row["total_pr_events"] or 0),
        "First Active":     str(row["first_active_date"]),
        "Last Active":      str(row["last_active_date"]),
    }


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_repo_daily_activity(repo_name: str, start_date, end_date) -> pd.DataFrame:
    """
    Return daily activity for a single repository over a date range.

    Source: fct_github_daily_activity

    Args:
        repo_name:   Repository to filter
        start_date:  Range start (date or str)
        end_date:    Range end (date or str)

    Returns:
        DataFrame columns: activity_date, commit_count, push_count,
                           push_avg_commits, pr_event_count, pr_opened,
                           pr_merged, pr_closed, pr_merged_pct,
                           total_activity_count
    """
    conn = get_connection()
    query = """
        SELECT
            activity_date::date       AS activity_date,
            commit_count,
            push_count,
            push_avg_commits,
            pr_event_count,
            pr_opened,
            pr_merged,
            pr_closed,
            pr_merged_pct,
            total_activity_count
        FROM fct_github_daily_activity
        WHERE repo_name = %s
          AND activity_date BETWEEN %s AND %s
        ORDER BY activity_date
    """
    df = pd.read_sql(query, conn, params=[repo_name, start_date, end_date])
    if not df.empty:
        df["activity_date"] = pd.to_datetime(df["activity_date"]).dt.strftime("%Y-%m-%d")
    return df


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_repo_summary_table(start_date, end_date) -> pd.DataFrame:
    """
    Return a summary comparison table for all repos over a date range.

    Used as the Detailed Table section of the Repository Analytics page.
    Source: fct_github_daily_activity aggregated by repo_name.

    Args:
        start_date: Range start
        end_date:   Range end

    Returns:
        DataFrame columns: repo_name, total_commits, total_pushes,
                           total_pr_events, pr_merged, avg_merge_rate
    """
    conn = get_connection()
    query = """
        SELECT
            repo_name,
            SUM(commit_count)       AS total_commits,
            SUM(push_count)         AS total_pushes,
            SUM(pr_event_count)     AS total_pr_events,
            SUM(pr_merged)          AS pr_merged,
            ROUND(AVG(pr_merged_pct), 2) AS avg_merge_rate_pct
        FROM fct_github_daily_activity
        WHERE activity_date BETWEEN %s AND %s
        GROUP BY repo_name
        ORDER BY total_commits DESC
    """
    return pd.read_sql(query, conn, params=[start_date, end_date])
