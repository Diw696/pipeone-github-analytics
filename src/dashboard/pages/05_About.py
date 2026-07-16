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
    **PipeOne** is an end-to-end GitHub Analytics Data Engineering project.

    It demonstrates a complete, production-style data pipeline that:
    - Ingests live GitHub events (push, pull request) via the GitHub REST API
    - Stores raw events in a PostgreSQL data warehouse
    - Transforms data through three dbt layers (Bronze → Silver → Gold)
    - Orchestrates the full pipeline with Apache Airflow
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
    ┌─────────────────────────────────────────────────────────────────┐
    │                     PipeOne Data Pipeline                       │
    └─────────────────────────────────────────────────────────────────┘

    GitHub REST API
         │
         │  Python requests (src/ingestion/github_client.py)
         ▼
    PostgreSQL — github_events_raw
         │
         │  dbt Bronze (staging models)
         │  Light selection, no transformation
         ▼
    dbt Silver — int_push_events, int_pull_requests
         │
         │  Business rules, typing, deduplication
         ▼
    dbt Gold — dim_repository, dim_contributor,
               fct_github_daily_activity,
               fct_contributor_daily_activity
         │
         │  Pre-computed metrics, surrogate keys, quality tests
         ▼
    Apache Airflow — pipeone_pipeline DAG
         │
         │  Orchestrates: ingest → dbt run → dbt test
         ▼
    Streamlit Analytics Dashboard  ← You are here
         │
         │  Reads from Gold Layer only
         └──────────────────────────────────────────────
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

    | Layer | dbt Models | Purpose |
    |---|---|---|
    | **Bronze** (Staging) | `stg_github_events` | Raw field selection. Minimal transformation. Closest to source. |
    | **Silver** (Intermediate) | `int_push_events`, `int_pull_requests` | Business rule application. Type casting. Deduplication. Event classification. |
    | **Gold** (Final) | `dim_repository`, `dim_contributor`, `fct_github_daily_activity`, `fct_contributor_daily_activity` | Conformed dimensions. Fact tables. Pre-computed metrics. Surrogate keys. dbt quality tests. |

    The dashboard reads **only from the Gold Layer**. This ensures:
    - All metrics are defined once, in SQL, and tested by dbt
    - The dashboard cannot show a metric that has not been validated
    - Metric definitions change in dbt — the dashboard reflects changes automatically
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
        "Source of GitHub push and pull request events",
        "Central data warehouse — raw, Bronze, Silver, and Gold layers",
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
    The Python ingestion script polls the GitHub REST API for `PushEvent` and
    `PullRequestEvent` entries across the three tracked repositories.
    Each event is stored as a raw JSON payload in `github_events_raw` (PostgreSQL).

    **Step 2 — Bronze Transformation (dbt)**
    dbt staging models select relevant fields from `github_events_raw`.
    No business logic is applied. Output: clean, typed source data.

    **Step 3 — Silver Transformation (dbt)**
    Intermediate models apply business rules:
    parsing push commit counts, classifying PR actions (opened/closed/merged),
    and linking events to their source repository.

    **Step 4 — Gold Transformation (dbt)**
    Final models build the analytics-ready tables:
    - `dim_repository` — one row per repo, all-time metrics denormalized
    - `dim_contributor` — one row per contributor, type-classified
    - `fct_github_daily_activity` — daily metrics per repo with pre-computed rates
    - `fct_contributor_daily_activity` — daily metrics per contributor per repo

    dbt quality tests (unique, not_null, accepted_values, relationships) run
    after each transformation to validate the Gold Layer before it is served.

    **Step 5 — Orchestration (Airflow)**
    The `pipeone_pipeline` DAG coordinates all steps:
    ingest → dbt run (Bronze) → dbt run (Silver) → dbt run (Gold) → dbt test.
    The DAG runs on a schedule and logs every execution result.

    **Step 6 — Presentation (This Dashboard)**
    Streamlit reads from the Gold Layer. Every chart and metric in this
    dashboard traces back to a specific dbt model and a tested column.
    """
)
st.divider()

# ---------------------------------------------------------------------------
# Developer Information
# ---------------------------------------------------------------------------
st.subheader("Developer")
st.markdown(
    """
    **Project:** PipeOne — GitHub Analytics Data Engineering Pipeline

    **Developer:** Diwakar Kaushik

    **Project Scope:** End-to-end data engineering — API ingestion, warehouse design,
    dbt transformation (Bronze/Silver/Gold), Airflow orchestration, and analytics dashboard.

    **GitHub Repository:** [github.com/Diw696/pipeone-github-analytics](https://github.com/Diw696/pipeone-github-analytics)
    """
)
