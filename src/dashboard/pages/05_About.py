"""
Page 5: About Project
======================
Business question: "How does PipeOne work?"

Layout:
  Title → Description → (no filters) → (no KPIs) → Sections → Table

Static informational page. No data loading.
Provides project context for mentors, recruiters, and presenters.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.title("ℹ️ About PipeOne")
st.markdown(
    "**Business question:** How does PipeOne work?"
)
st.markdown(
    "This page provides full context on the PipeOne project — its purpose, "
    "architecture, technology stack, and workflow. Designed for presentation "
    "and portfolio review."
)
st.divider()

# ---------------------------------------------------------------------------
# Project Overview
# ---------------------------------------------------------------------------
st.subheader("Project Overview")
st.markdown(
    """
    **PipeOne** is an end-to-end Developer Intelligence Platform.
 
    It demonstrates a complete, production-style data pipeline that:
    - Ingests software engineering signals from multiple sources:
      1. **GitHub REST API** (live push and pull request events)
      2. **Hacker News Firebase API** (top stories, score, comments, links)
    - Stores raw signals in a PostgreSQL data warehouse
    - Transforms data through three dbt layers (Bronze → Silver → Gold)
    - Integrates cross-source analytics by cross-referencing repository names in HN titles
    - Orchestrates the full multi-source pipeline with Apache Airflow
    - Presents insights through this Streamlit analytics dashboard
 
    **Tracked Repositories:**
    - `facebook/react` — JavaScript UI library
    - `microsoft/vscode` — TypeScript code editor
    - `vercel/next.js` — JavaScript full-stack framework
    """
)
st.divider()

# ---------------------------------------------------------------------------
# Architecture Diagram (text-based)
# ---------------------------------------------------------------------------
st.subheader("System Architecture")
st.markdown(
    """
    ```
    ┌─────────────────────────────────────────────────────────────────────────┐
    │              PipeOne Multi-Source Developer Intelligence                │
    └─────────────────────────────────────────────────────────────────────────┘

        GitHub API                                   Hacker News API
            │                                               │
            │ Ingestion Ingestor                            │ Ingestion Client
            ▼                                               ▼
    PostgreSQL: github_events_raw                   PostgreSQL: hn_stories_raw
            │                                               │
            │ dbt Bronze (staging)                          │ dbt Bronze (staging)
            ▼                                               ▼
    dbt Bronze: stg_github_events                   dbt Bronze: stg_hn_stories
            │                                               │
            │ dbt Silver (intermediate)                     │ dbt Silver (intermediate)
            ▼                                               ▼
    dbt Silver: int_push_events                     dbt Silver: int_hn_stories
                int_pull_requests                               int_hn_repo_mentions
            │                                               │
            └───────────────┬───────────────────────────────┘
                            │
                            │ dbt Gold (analytics-ready serving layer)
                            ▼
    dbt Gold:   dim_repository, dim_contributor, dim_hn_story
                fct_github_daily_activity, fct_contributor_daily_activity
                fct_hn_daily_activity, fct_hn_repo_mentions
                            │
                            ▼
               Apache Airflow Ingestion DAG (pipeone_pipeline)
                            │
                            ▼
               Streamlit Analytics Dashboard (You are here)
    ```
    """
)
st.divider()

# ---------------------------------------------------------------------------
# Medallion Architecture
# ---------------------------------------------------------------------------
st.subheader("Medallion Architecture")
st.markdown(
    """
    PipeOne implements the **Medallion Architecture** — a layered data
    transformation pattern that separates concerns across three quality tiers:
 
    | Layer | GitHub dbt Models | Hacker News dbt Models | Purpose |
    |---|---|---|---|
    | **Bronze** (Staging) | `stg_github_events` | `stg_hn_stories` | Raw field selection. Minimal transformation. |
    | **Silver** (Intermediate) | `int_push_events`, `int_pull_requests` | `int_hn_stories`, `int_hn_repo_mentions` | Typing. Deduplication. Regex mention pattern matching. |
    | **Gold** (Final Serving) | `dim_repository`, `dim_contributor`, `fct_github_daily_activity`, `fct_contributor_daily_activity` | `dim_hn_story`, `fct_hn_daily_activity`, `fct_hn_repo_mentions` | Conformed dimensions. Aggregated daily facts. Cross-source mention metrics. dbt quality tests. |
 
    The dashboard reads **only from the Gold Layer** and mention-bridge Silver layer. This ensures:
    - All metrics are defined once in SQL and tested by dbt.
    - The dashboard cannot show a metric that has not been validated by schema quality tests.
    - Definitions change in dbt, and the dashboard reflects changes automatically.
    """
)
st.divider()

# ---------------------------------------------------------------------------
# Technology Stack
# ---------------------------------------------------------------------------
st.subheader("Technology Stack")

stack_data = {
    "Tool": [
        "Python",
        "GitHub REST API",
        "Hacker News Firebase API",
        "PostgreSQL",
        "dbt (data build tool)",
        "Apache Airflow",
        "Streamlit",
        "Plotly",
        "psycopg2",
        "python-dotenv",
        "Docker + Docker Compose",
    ],
    "Role": [
        "Data ingestion scripting and orchestration logic",
        "Source of GitHub activity events",
        "Source of community stories and traction upvotes",
        "Central data warehouse storing raw, Bronze, Silver, and Gold layers",
        "SQL transformation framework — models, tests, documentation",
        "Pipeline orchestration — scheduling and DAG management",
        "Analytics dashboard — presentation layer",
        "Interactive charts and visualisations",
        "PostgreSQL database adapter for Python",
        "Environment variable management",
        "Local infrastructure — database and Airflow containers",
    ],
}

import pandas as pd
stack_df = pd.DataFrame(stack_data)
st.dataframe(stack_df, use_container_width=True, hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# Project Workflow
# ---------------------------------------------------------------------------
st.subheader("End-to-End Project Workflow")
st.markdown(
    """
    **Step 1 — Ingestion**
    The Python ingestion scripts independently extract signals from the GitHub REST API (events)
    and the Hacker News Firebase API (top stories). Raw data is stored in the PostgreSQL warehouse.
 
    **Step 2 — Bronze Transformation (dbt)**
    dbt staging models select and type fields from raw tables (`github_events_raw` and `hn_stories_raw`).
 
    **Step 3 — Silver Transformation (dbt)**
    Intermediate models apply clean typing and deduplication, and extract mentions of our tracked
    repositories from Hacker News story titles using PostgreSQL regex word boundaries.
 
    **Step 4 — Gold Transformation (dbt)**
    Final models build conformed dimension and daily fact tables:
    - `dim_repository` / `dim_contributor` / `dim_hn_story` — Entity dimensions
    - `fct_github_daily_activity` / `fct_hn_daily_activity` — Daily metrics
    - `fct_hn_repo_mentions` — Repository mention counts and upvote scores
 
    dbt quality tests (unique, not_null, accepted_values, relationships) run to validate tables before serving.
 
    **Step 5 — Orchestration (Airflow)**
    The Airflow DAG runs tasks sequentially:
    GitHub ingest → HN ingest → dbt build → dbt test.
 
    **Step 6 — Presentation (This Dashboard)**
    Streamlit visualizes conformed Gold Layer metrics with side-by-side comparison.
    """
)
st.divider()

# ---------------------------------------------------------------------------
# Developer Information
# ---------------------------------------------------------------------------
st.subheader("Developer")
st.markdown(
    """
    **Project:** PipeOne — Developer Intelligence Platform
 
    **Developer:** Diwakar Kaushik
 
    **Project Scope:** Multi-source data engineering — API ingestion, warehouse design,
    dbt transformation (Bronze/Silver/Gold), Airflow orchestration, and analytics dashboard.
 
    **GitHub Repository:** [github.com/Diw696/pipeone-github-analytics](https://github.com/Diw696/pipeone-github-analytics)
    """
)
