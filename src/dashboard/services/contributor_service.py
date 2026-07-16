"""
Contributor Service
===================
Data access for the Contributor Analytics page.

Business question answered: "Who is contributing the most?"

Combines dim_contributor (who they are) with
fct_contributor_daily_activity (what they did, per day, per repo).

All pre-computed Gold fields are used as-is:
  contrib_type, total_activity_count, pr_merged_pct, contribution_type

Author: PipeOne Project
"""

import pandas as pd
import streamlit as st
from services.db import get_connection
from config.settings import CACHE_TTL_SEC


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_contributor_leaderboard(
    repo_name: str = "All",
    contrib_type: str = "All",
) -> pd.DataFrame:
    """
    Return ranked contributor list with all-time totals, ordered by Total Activity.

    Source: dim_contributor joined with optional repo filter from
            fct_contributor_daily_activity.

    When repo_name is "All", reads from dim_contributor directly.
    When a specific repo is selected, filters through the fact table.

    Args:
        repo_name:    "All" or a specific repo name
        contrib_type: "All", "push_only", "pr_only", or "both"

    Returns:
        DataFrame columns: rank, username, contrib_type, total_activity,
                           total_push_events, total_pr_events
    """
    conn = get_connection()

    if repo_name == "All":
        type_filter = "" if contrib_type == "All" else "WHERE contrib_type = %s"
        params = [] if contrib_type == "All" else [contrib_type]
        query = f"""
            SELECT
                ROW_NUMBER() OVER (ORDER BY (total_push_events + total_pr_events) DESC) AS rank,
                username,
                contrib_type,
                (total_push_events + total_pr_events) AS total_activity,
                total_push_events,
                total_pr_events
            FROM dim_contributor
            {type_filter}
            ORDER BY total_activity DESC
        """
    else:
        type_filter = "" if contrib_type == "All" else "AND d.contrib_type = %s"
        params = [repo_name] + ([contrib_type] if contrib_type != "All" else [])
        query = f"""
            SELECT
                ROW_NUMBER() OVER (ORDER BY SUM(f.total_activity_count) DESC) AS rank,
                d.username,
                d.contrib_type,
                SUM(f.total_activity_count) AS total_activity,
                SUM(f.push_count)           AS total_push_events,
                SUM(f.pr_event_count)       AS total_pr_events
            FROM fct_contributor_daily_activity f
            JOIN dim_contributor d ON f.username = d.username
            WHERE f.repo_name = %s
            {type_filter}
            GROUP BY d.username, d.contrib_type
            ORDER BY total_activity DESC
        """

    return pd.read_sql(query, conn, params=params)


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_contrib_type_distribution() -> pd.DataFrame:
    """
    Return count of contributors per contrib_type.

    Used to render the contribution-type donut chart.
    Source: dim_contributor

    Returns:
        DataFrame columns: contrib_type, contributor_count
    """
    conn = get_connection()
    query = """
        SELECT
            contrib_type,
            COUNT(*) AS contributor_count
        FROM dim_contributor
        GROUP BY contrib_type
        ORDER BY contributor_count DESC
    """
    return pd.read_sql(query, conn)


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_top_by_total_activity(repo_name: str = "All", top_n: int = 10) -> pd.DataFrame:
    """
    Return top N contributors by total_activity_count.

    total_activity_count is pre-computed by dbt as push_count + pr_event_count.
    Source: fct_contributor_daily_activity (filtered) or dim_contributor (all)

    Args:
        repo_name: "All" or specific repo
        top_n:     How many contributors to return

    Returns:
        DataFrame columns: username, total_activity_count
    """
    conn = get_connection()

    if repo_name == "All":
        query = """
            SELECT
                username,
                SUM(total_activity_count) AS total_activity_count
            FROM fct_contributor_daily_activity
            GROUP BY username
            ORDER BY total_activity_count DESC
            LIMIT %s
        """
        params = [top_n]
    else:
        query = """
            SELECT
                username,
                SUM(total_activity_count) AS total_activity_count
            FROM fct_contributor_daily_activity
            WHERE repo_name = %s
            GROUP BY username
            ORDER BY total_activity_count DESC
            LIMIT %s
        """
        params = [repo_name, top_n]

    return pd.read_sql(query, conn, params=params)


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_contributor_list() -> list[str]:
    """
    Return all contributor usernames sorted alphabetically.

    Source: dim_contributor

    Returns:
        List of username strings
    """
    conn = get_connection()
    query = "SELECT username FROM dim_contributor ORDER BY username"
    df = pd.read_sql(query, conn)
    return df["username"].tolist()


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_contributor_profile(username: str) -> dict:
    """
    Return all-time profile data for a single contributor (omitting commits).

    Source: dim_contributor

    Args:
        username: GitHub handle

    Returns:
        dict with keys: username, contrib_type, total_push_events,
                        total_pr_events, first_active_date, last_active_date
    """
    conn = get_connection()
    query = """
        SELECT
            username,
            contrib_type,
            total_push_events,
            total_pr_events,
            first_active_date,
            last_active_date
        FROM dim_contributor
        WHERE username = %s
    """
    df = pd.read_sql(query, conn, params=[username])
    if df.empty:
        return {}
    row = df.iloc[0]
    return {
        "Username":         row["username"],
        "Contributor Type": row["contrib_type"],
        "Total Pushes":     int(row["total_push_events"] or 0),
        "Total PR Events":  int(row["total_pr_events"] or 0),
        "First Active":     str(row["first_active_date"]),
        "Last Active":      str(row["last_active_date"]),
    }


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_contributor_timeline(username: str, start_date, end_date) -> pd.DataFrame:
    """
    Return daily activity breakdown for a single contributor.
    Casts activity_date to date and formats it as YYYY-MM-DD.

    Source: fct_contributor_daily_activity
    Grain: one row per (contributor, repo, date)

    Args:
        username:   GitHub handle
        start_date: Range start
        end_date:   Range end

    Returns:
        DataFrame columns: activity_date, repo_name, push_count,
                           pr_event_count, pr_opened, pr_merged,
                           pr_merged_pct, contribution_type,
                           total_activity_count
    """
    conn = get_connection()
    query = """
        SELECT
            activity_date::date           AS activity_date,
            repo_name,
            push_count,
            pr_event_count,
            pr_opened,
            pr_merged,
            pr_merged_pct,
            contribution_type,
            total_activity_count
        FROM fct_contributor_daily_activity
        WHERE username = %s
          AND activity_date BETWEEN %s AND %s
        ORDER BY activity_date, repo_name
    """
    df = pd.read_sql(query, conn, params=[username, start_date, end_date])
    if not df.empty:
        df["activity_date"] = pd.to_datetime(df["activity_date"]).dt.strftime("%Y-%m-%d")
    return df


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_contributor_repo_participation(username: str) -> pd.DataFrame:
    """
    Return per-repository breakdown for a single contributor (all time, omitting commits).

    Source: fct_contributor_daily_activity aggregated by repo

    Args:
        username: GitHub handle

    Returns:
        DataFrame columns: repo_name, total_pushes, total_pr_events,
                           pr_merged, avg_merge_rate_pct
    """
    conn = get_connection()
    query = """
        SELECT
            repo_name,
            SUM(push_count)               AS total_pushes,
            SUM(pr_event_count)           AS total_pr_events,
            SUM(pr_merged)                AS pr_merged,
            ROUND(AVG(pr_merged_pct), 2)  AS avg_merge_rate_pct
        FROM fct_contributor_daily_activity
        WHERE username = %s
        GROUP BY repo_name
        ORDER BY (SUM(push_count) + SUM(pr_event_count)) DESC
    """
    return pd.read_sql(query, conn, params=[username])
