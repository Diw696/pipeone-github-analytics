"""
Dashboard Configuration
=======================
Loads PostgreSQL credentials from the project .env file.

Uses python-dotenv, consistent with the rest of PipeOne.
No new environment variables are introduced here — all keys
already exist in the project .env from Week 1.

Author: PipeOne Project
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve .env from project root (two levels above src/dashboard/config/)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_ENV_PATH = _PROJECT_ROOT / ".env"

load_dotenv(dotenv_path=_ENV_PATH)


def get_db_config() -> dict:
    """
    Return a dictionary of PostgreSQL connection parameters.

    Reads from the project .env file using the same keys
    established in src/database/init_db.py.

    Returns:
        dict: Connection parameters for psycopg2.connect(**config)
    """
    return {
        "host":     os.getenv("POSTGRES_HOST", "localhost"),
        "port":     int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname":   os.getenv("POSTGRES_DB", "pipeone_warehouse"),
        "user":     os.getenv("POSTGRES_USER", "pipeone_user"),
        "password": os.getenv("POSTGRES_PASSWORD"),
    }


# Project-level constants shared across dashboard pages
APP_TITLE       = "PipeOne — Developer Intelligence"
APP_ICON        = "📊"
REPOS           = ["facebook/react", "microsoft/vscode", "vercel/next.js"]
GOLD_SCHEMA     = "public"   # dbt Gold models materialise in public schema
CACHE_TTL_SEC   = 300        # 5 minutes — refresh interval for cached DataFrames

# Hacker News Gold tables — used by Pipeline Health for monitoring
HN_GOLD_TABLES  = ["dim_hn_story", "fct_hn_daily_activity", "fct_hn_repo_mentions"]

