"""
PipeOne Analytics Dashboard — Entrypoint
=========================================
Uses st.navigation() to register all pages with explicit titles.
This is what renames the sidebar entry from "app" to "Home".

All page content for the landing page lives in the home() function below.
All other pages remain in their existing files under pages/.

Run with:
    streamlit run src/dashboard/app.py

Author: PipeOne Project
"""

import sys
from pathlib import Path

_DASHBOARD_DIR = Path(__file__).resolve().parent
if str(_DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_DIR))

import streamlit as st
from config.settings import APP_TITLE, APP_ICON

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Home page content (function-based so st.navigation can register it)
# ---------------------------------------------------------------------------

def home():
    """Landing page content rendered when the user selects Home."""

    st.title("📊 PipeOne — Developer Intelligence")
    st.markdown("### Multi-Source Platform Evolution")
    st.markdown(
        "An end-to-end Developer Intelligence Platform that ingests software engineering signals "
        "from multiple sources (GitHub events + Hacker News stories), "
        "transforms them through a Medallion Architecture (Bronze → Silver → Gold) using dbt, "
        "and presents insights through this analytics dashboard."
    )
    st.divider()

    # Navigation guide — 5 cards
    st.subheader("Dashboard Pages")
    st.markdown("Use the sidebar to navigate between pages.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            #### 🏠 Overview
            **Business question:** What is happening overall?

            Platform-wide KPIs, daily activity trends, and repository
            comparison across all three tracked repositories, with a Community Pulse teaser.
            """
        )
        st.markdown(
            """
            #### 👤 Contributor Analytics
            **Business question:** Who is contributing the most?

            Contributor leaderboard, type distribution, and individual
            contributor profiles with activity timelines.
            """
        )
        st.markdown(
            """
            #### 🔥 Community Traction
            **Business question:** How are our tracked projects trending in the developer community?

            Deep-dive Hacker News analytics, repository mentions, daily story volume,
            top community authors, and trending headlines.
            """
        )

    with col2:
        st.markdown(
            """
            #### 📂 Repository Analytics
            **Business question:** Which repository is performing best?

            Per-repository KPIs, commit and push trends, PR merge
            velocity analysis, and Hacker News community mentions.
            """
        )
        st.markdown(
            """
            #### 🩺 Pipeline Health
            **Business question:** Can I trust this data?

            Gold Layer table freshness, row counts, data coverage, and
            pipeline lifecycle status across both GitHub and Hacker News ingestion pipelines.
            """
        )

    st.divider()

    # Architecture table
    st.subheader("Data Pipeline")
    st.markdown(
        """
        | Stage | Tool | Purpose |
        |---|---|---|
        | **Ingestion** | Python + GitHub & HN APIs | Fetch GitHub activity events and Hacker News stories |
        | **Warehouse** | PostgreSQL | Store raw events and story payloads |
        | **Bronze** | dbt staging | Select, clean, and type raw fields |
        | **Silver** | dbt intermediate | Parse payloads, normalize data, and detect repository mentions |
        | **Gold** | dbt final models | Analytics-ready dimensions and facts |
        | **Orchestration** | Apache Airflow | Schedule and monitor the full multi-source pipeline |
        | **Dashboard** | Streamlit | Present Gold Layer metrics (you are here) |
        """
    )

    st.divider()

    # Tracked repositories
    st.subheader("Tracked Repositories")
    r1, r2, r3 = st.columns(3)
    with r1:
        st.metric(label="facebook/react", value="JavaScript", delta="~225K ⭐")
    with r2:
        st.metric(label="microsoft/vscode", value="TypeScript", delta="~165K ⭐")
    with r3:
        st.metric(label="vercel/next.js", value="JavaScript", delta="~125K ⭐")

    st.caption("Navigate to any page in the sidebar to begin exploring the data.")


# ---------------------------------------------------------------------------
# Navigation — registers all pages with explicit sidebar titles
# st.navigation() is the Streamlit-native way to control sidebar page names.
# Without it, the root app.py shows as "app" in the sidebar.
# ---------------------------------------------------------------------------

pg = st.navigation(
    [
        st.Page(home,                                title="Home",                   icon="🏠"),
        st.Page("pages/01_Overview.py",              title="Overview",               icon="📊"),
        st.Page("pages/02_Repository_Analytics.py",  title="Repository Analytics",   icon="📂"),
        st.Page("pages/03_Contributor_Analytics.py", title="Contributor Analytics",  icon="👤"),
        st.Page("pages/06_Community_Traction.py",    title="Community Traction",     icon="🔥"),
        st.Page("pages/04_Pipeline_Health.py",       title="Pipeline Health",        icon="🩺"),
        st.Page("pages/05_About.py",                 title="About",                  icon="ℹ️"),
    ]
)

pg.run()
