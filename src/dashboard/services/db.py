"""
Database Connection
===================
Provides a single, cached PostgreSQL connection for the dashboard.

Pattern:
    @st.cache_resource creates the connection once per server process
    and reuses it across all Streamlit reruns and sessions.

    This is Streamlit's recommended pattern for shared resources.
    A connection pool is not used because this dashboard serves a
    small, known audience (demo, mentors, recruiters).

Author: PipeOne Project
"""

import psycopg2
import streamlit as st
from config.settings import get_db_config


@st.cache_resource
def get_connection():
    """
    Open and cache a single PostgreSQL connection.

    Called on first use and reused for the lifetime of the server process.
    Uses the same .env keys as src/database/init_db.py.

    Returns:
        psycopg2.connection: Active database connection
    """
    config = get_db_config()
    try:
        conn = psycopg2.connect(**config)
        return conn
    except psycopg2.Error as e:
        st.error(
            f"❌ Could not connect to PostgreSQL.\n\n"
            f"Check your .env credentials and confirm the database is running.\n\n"
            f"Error: {e}"
        )
        st.stop()
