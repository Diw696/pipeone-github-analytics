"""
Hacker News Service
===================
Data access for the Hacker News page and other pages displaying HN traction.

All metrics are read directly from the Gold Layer (dim_hn_story,
fct_hn_daily_activity, fct_hn_repo_mentions).

Author: PipeOne Project
"""

import pandas as pd
import streamlit as st
from services.db import get_connection
from config.settings import CACHE_TTL_SEC


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_hn_platform_kpis() -> dict:
    """
    Return Hacker News platform-wide KPI totals and averages.

    Source: dim_hn_story, fct_hn_daily_activity

    Returns:
        dict with keys: total_stories, avg_score, unique_authors, total_comments
    """
    conn = get_connection()
    query = """
        SELECT
            COUNT(story_id)        AS total_stories,
            AVG(score)              AS avg_score,
            COUNT(DISTINCT author)  AS unique_authors,
            SUM(comment_count)     AS total_comments
        FROM dim_hn_story
    """
    df = pd.read_sql(query, conn)
    if df.empty:
        return {
            "Total HN Stories": 0,
            "Average Score": 0.0,
            "Unique Authors": 0,
            "Total Comments": 0,
        }
    row = df.iloc[0]
    return {
        "Total HN Stories": int(row["total_stories"] or 0),
        "Average Score": float(round(row["avg_score"] or 0.0, 1)),
        "Unique Authors": int(row["unique_authors"] or 0),
        "Total Comments": int(row["total_comments"] or 0),
    }


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_hn_daily_activity(start_date, end_date) -> pd.DataFrame:
    """
    Return daily Hacker News metrics.

    Source: fct_hn_daily_activity

    Args:
        start_date: Filter start date or string
        end_date:   Filter end date or string

    Returns:
        DataFrame columns: activity_date, story_count, total_score,
                           avg_score, total_comments, avg_comments,
                           unique_authors, top_score, stories_with_url_pct
    """
    conn = get_connection()
    query = """
        SELECT
            activity_date,
            story_count,
            total_score,
            avg_score,
            total_comments,
            avg_comments,
            unique_authors,
            top_score,
            stories_with_url_pct
        FROM fct_hn_daily_activity
        WHERE activity_date BETWEEN %s AND %s
        ORDER BY activity_date
    """
    return pd.read_sql(query, conn, params=[start_date, end_date])


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_hn_trending_stories(limit: int = 10) -> pd.DataFrame:
    """
    Return highest scoring Hacker News stories.

    Source: dim_hn_story

    Args:
        limit: Max number of stories to return

    Returns:
        DataFrame columns: story_id, title, author, url, score, comment_count, published_at
    """
    conn = get_connection()
    query = """
        SELECT
            story_id,
            title,
            author,
            url,
            score,
            comment_count,
            published_at
        FROM dim_hn_story
        ORDER BY score DESC, comment_count DESC
        LIMIT %s
    """
    return pd.read_sql(query, conn, params=[limit])


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_hn_top_authors(limit: int = 10) -> pd.DataFrame:
    """
    Return the most active authors by story count on Hacker News.

    Source: dim_hn_story

    Args:
        limit: Max number of authors to return

    Returns:
        DataFrame columns: author, story_count, total_score
    """
    conn = get_connection()
    query = """
        SELECT
            author,
            COUNT(story_id)  AS story_count,
            SUM(score)        AS total_score
        FROM dim_hn_story
        WHERE author IS NOT NULL
        GROUP BY author
        ORDER BY story_count DESC, total_score DESC
        LIMIT %s
    """
    return pd.read_sql(query, conn, params=[limit])


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_hn_repo_mentions(start_date, end_date) -> pd.DataFrame:
    """
    Return daily repository mention activity.

    Source: fct_hn_repo_mentions

    Args:
        start_date: Filter start date or string
        end_date:   Filter end date or string

    Returns:
        DataFrame columns: mentioned_repo, activity_date, mention_count,
                           total_score, avg_score, total_comments, avg_comments, top_score
    """
    conn = get_connection()
    query = """
        SELECT
            mentioned_repo,
            activity_date,
            mention_count,
            total_score,
            avg_score,
            total_comments,
            avg_comments,
            top_score
        FROM fct_hn_repo_mentions
        WHERE activity_date BETWEEN %s AND %s
        ORDER BY activity_date, mentioned_repo
    """
    return pd.read_sql(query, conn, params=[start_date, end_date])


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_hn_repo_mention_summary(start_date=None, end_date=None) -> pd.DataFrame:
    """
    Return aggregated mention counts by repository.

    Source: fct_hn_repo_mentions

    Returns:
        DataFrame columns: mentioned_repo, total_mentions, total_score, total_comments
    """
    conn = get_connection()
    if start_date and end_date:
        query = """
            SELECT
                mentioned_repo,
                SUM(mention_count)  AS total_mentions,
                SUM(total_score)    AS total_score,
                SUM(total_comments) AS total_comments
            FROM fct_hn_repo_mentions
            WHERE activity_date BETWEEN %s AND %s
            GROUP BY mentioned_repo
            ORDER BY total_mentions DESC
        """
        return pd.read_sql(query, conn, params=[start_date, end_date])
    else:
        query = """
            SELECT
                mentioned_repo,
                SUM(mention_count)  AS total_mentions,
                SUM(total_score)    AS total_score,
                SUM(total_comments) AS total_comments
            FROM fct_hn_repo_mentions
            GROUP BY mentioned_repo
            ORDER BY total_mentions DESC
        """
        return pd.read_sql(query, conn)


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_hn_recent_stories(limit: int = 10) -> pd.DataFrame:
    """
    Return the most recently fetched Hacker News stories.

    Source: dim_hn_story

    Args:
        limit: Max number of stories to return

    Returns:
        DataFrame columns: story_id, title, author, score, comment_count, published_at, url
    """
    conn = get_connection()
    query = """
        SELECT
            story_id,
            title,
            author,
            score,
            comment_count,
            published_at,
            url
        FROM dim_hn_story
        ORDER BY published_at DESC
        LIMIT %s
    """
    return pd.read_sql(query, conn, params=[limit])


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_hn_repo_stories(repo_name: str, limit: int = 5) -> pd.DataFrame:
    """
    Return recent stories that mentioned a specific repository.

    Source: int_hn_repo_mentions

    Args:
        repo_name: Canonical repo name (e.g., 'facebook/react')
        limit: Max number of stories to return

    Returns:
        DataFrame columns: story_id, title, author, score, comment_count, published_at, url
    """
    conn = get_connection()
    query = """
        SELECT
            story_id,
            title,
            author,
            score,
            comment_count,
            published_at,
            url
        FROM int_hn_repo_mentions
        WHERE mentioned_repo = %s
        ORDER BY published_at DESC
        LIMIT %s
    """
    return pd.read_sql(query, conn, params=[repo_name, limit])


@st.cache_data(ttl=CACHE_TTL_SEC)
def get_hn_repo_mentions_over_time(repo_name: str, start_date, end_date) -> pd.DataFrame:
    """
    Return daily mentions and score trends for a specific repository.

    Source: fct_hn_repo_mentions

    Args:
        repo_name: Canonical repo name (e.g., 'facebook/react')
        start_date: Start date filter
        end_date: End date filter

    Returns:
        DataFrame columns: activity_date, mention_count, total_score, total_comments
    """
    conn = get_connection()
    query = """
        SELECT
            activity_date,
            mention_count,
            total_score,
            total_comments
        FROM fct_hn_repo_mentions
        WHERE mentioned_repo = %s AND activity_date BETWEEN %s AND %s
        ORDER BY activity_date
    """
    return pd.read_sql(query, conn, params=[repo_name, start_date, end_date])
