"""
pipeone_pipeline.py — PipeOne GitHub Analytics ELT Pipeline
============================================================

This DAG orchestrates the complete ELT pipeline for the PipeOne project.

Pipeline architecture:
    GitHub REST API
        ↓
    extract_github_events   (PythonOperator)
        ↓
    dbt_build               (BashOperator — Bronze → Silver → Gold)
        ↓
    dbt_test                (BashOperator — data quality gate, hard fail)

Repositories ingested:
    - facebook/react
    - microsoft/vscode
    - vercel/next.js

Schedule:
    None — manual trigger only (suitable for development and demo).
    To activate daily runs, change schedule=None to schedule="@daily".

Extending this DAG in the future:
    After dbt_test, you can chain additional tasks such as:
        dbt_test >> send_slack_notification
        dbt_test >> refresh_dashboard
        dbt_test >> export_to_bigquery
    The linear structure intentionally avoids complex branching so that
    future contributors can extend it with minimal friction.

Author:    PipeOne Data Engineering
Project:   PipeOne — GitHub Analytics (H3: Airflow Orchestration)
Airflow:   2.9.x
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator


# =============================================================================
# PATHS — module-level constants for easy maintenance
#
# These match the volume mounts defined in docker-compose.yml:
#   ./dbt_project  →  /opt/airflow/project/dbt_project   (dbt models)
#   ./airflow/dbt_profiles  →  /home/airflow/.dbt         (profiles.yml)
# =============================================================================
DBT_PROJECT_DIR = "/opt/airflow/project/dbt_project"
DBT_PROFILES_DIR = "/home/airflow/.dbt"
DBT_TARGET = "dev"  # Switch to "prod" to write to the dbt_prod schema


# =============================================================================
# DEFAULT ARGUMENTS
#
# These settings apply to every task in the DAG unless explicitly overridden
# at the individual task level. Defined here (not inline) for readability.
# =============================================================================
default_args = {
    # Displayed in the Airflow UI — identifies who owns this pipeline
    "owner": "pipeone",

    # False: each DAG run is independent and does not wait for the
    # previous run to succeed. This is safe because ingestion is idempotent
    # (ON CONFLICT DO NOTHING) and dbt models are rebuilt from scratch each run.
    "depends_on_past": False,

    # Retry once on failure before marking the task as permanently failed.
    # Handles transient errors: GitHub API timeouts, network blips,
    # or a brief PostgreSQL unavailability.
    "retries": 1,

    # Wait 5 minutes between the failure and the retry attempt.
    # GitHub's API rate limit resets every hour — 5 minutes is a reasonable
    # buffer for transient quota exhaustion without over-delaying the pipeline.
    "retry_delay": timedelta(minutes=5),

    # No email alerts (email backend not configured in this environment).
    # In production, set these to True and configure SMTP in Airflow settings.
    "email_on_failure": False,
    "email_on_retry": False,
}


# =============================================================================
# INGESTION CALLABLE
#
# Defined at module level (not inside the DAG block) following Airflow best
# practices — callable functions should be importable and testable independently.
#
# Why a wrapper function instead of calling main() directly?
#   The original github_client.py uses sys.exit(1) for fatal errors, which
#   raises SystemExit. Airflow can technically catch this, but it produces
#   a cryptic error in the UI. The wrapper converts SystemExit to a clear
#   RuntimeError with a helpful message — without touching the original script.
# =============================================================================
def run_github_ingestion() -> None:
    """
    Wrapper for the PipeOne GitHub ingestion script.

    Imports and calls main() from src/ingestion/github_client.py.
    The import is deferred to call-time (not module import time) so that
    the Airflow scheduler can parse this DAG file without requiring the
    src/ volume to be mounted during startup.

    Raises:
        RuntimeError: If the ingestion script exits with a non-zero code,
                      indicating a fatal error (missing token, DB failure, etc.)
    """
    try:
        # Deferred import — src/ is on PYTHONPATH=/opt/airflow/project
        # which is set in docker-compose.yml for all Airflow containers.
        from src.ingestion.github_client import main as ingestion_main

        ingestion_main()

    except SystemExit as exc:
        # sys.exit(0) or sys.exit(None) = success, let it pass through.
        # Anything else = the script encountered a fatal error.
        if exc.code not in (None, 0):
            raise RuntimeError(
                f"GitHub ingestion script exited with code {exc.code}. "
                "Common causes: missing GITHUB_TOKEN environment variable, "
                "PostgreSQL connection refused, or POSTGRES_PASSWORD not set. "
                "Check task logs for the full traceback."
            ) from exc


# =============================================================================
# DAG DEFINITION
# =============================================================================
with DAG(
    # Unique identifier — appears in the Airflow UI, API, and CLI
    dag_id="pipeone_pipeline",

    # Human-readable summary shown in the DAG list view
    description=(
        "PipeOne ELT: GitHub API → PostgreSQL raw ingestion → "
        "dbt Bronze/Silver/Gold transformation → data quality validation."
    ),

    default_args=default_args,

    # Manual trigger only during development and presentation.
    # No automatic scheduling — the pipeline runs only when triggered via:
    #   - Airflow UI (Trigger DAG button)
    #   - CLI: airflow dags trigger pipeone_pipeline
    #   - Airflow REST API
    schedule=None,

    # Required by Airflow but irrelevant when schedule=None.
    # Fixed past date prevents accidental backfilling if schedule is later enabled.
    start_date=datetime(2026, 1, 1),

    # Prevents Airflow from generating historical runs for all past intervals
    # between start_date and today when the DAG is first enabled.
    catchup=False,

    # Used for filtering in the Airflow UI DAG list
    tags=["pipeone", "github", "dbt", "elt"],

    # Rendered in the Airflow UI DAG detail page
    doc_md="""
    # PipeOne ELT Pipeline

    Orchestrates the complete GitHub Analytics data pipeline.

    ## Flow
    ```
    extract_github_events → dbt_build → dbt_test
    ```

    ## Trigger
    Manual only (`schedule=None`). Trigger via the Airflow UI or CLI.

    ## Failure Behaviour
    Any task failure stops downstream execution immediately.
    `dbt_test` failures are hard failures — broken data is never silently accepted.

    ## Extending
    Add new tasks after `dbt_test`:
    ```python
    dbt_test >> send_slack_notification
    dbt_test >> refresh_dashboard
    ```
    """,
) as dag:

    # =========================================================================
    # TASK 1 — extract_github_events
    # =========================================================================
    # Calls the existing GitHubClient pipeline (src/ingestion/github_client.py).
    # This task does NOT modify any logic in the original script — it simply
    # invokes it as a Python callable inside the Airflow worker process.
    #
    # What happens inside:
    #   1. Authenticates with the GitHub REST API using GITHUB_TOKEN
    #   2. Checks rate limit before each request
    #   3. Fetches up to 30 events per repository (3 repos = up to 90 events)
    #   4. Writes raw JSON payloads to public.github_events_raw via psycopg2
    #   5. Skips duplicate events (ON CONFLICT DO NOTHING on event_id PK)
    #
    # Environment variables (injected by docker-compose.yml):
    #   GITHUB_TOKEN, POSTGRES_HOST (=warehouse), POSTGRES_PORT,
    #   POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
    # =========================================================================
    extract_github_events = PythonOperator(
        task_id="extract_github_events",
        python_callable=run_github_ingestion,
        doc_md="""
        ## Task: extract_github_events

        **Type**: PythonOperator

        Fetches recent GitHub events for 3 target repositories and writes raw
        JSON payloads to the `public.github_events_raw` table in PostgreSQL.

        **Repositories**: `facebook/react`, `microsoft/vscode`, `vercel/next.js`

        **Idempotency**: Safe to re-run — duplicate events are silently skipped
        via `ON CONFLICT (event_id) DO NOTHING`.

        **Retry**: 1 retry with 5-minute delay (GitHub rate limit buffer).
        """,
    )

    # =========================================================================
    # TASK 2 — dbt_build
    # =========================================================================
    # Runs `dbt build` which executes all models in the correct dependency order
    # as defined by the dbt DAG (ref() relationships between models):
    #
    #   stg_github_events (Bronze/staging, view)
    #       ↓
    #   int_push_events, int_pull_requests (Silver, views)
    #       ↓
    #   dim_repository, dim_contributor,
    #   fct_github_daily_activity, fct_contributor_daily_activity (Gold)
    #
    # Why `dbt build` and not `dbt run`?
    #   `dbt build` is the modern recommended command (dbt 1.0+). It combines
    #   `dbt run` + `dbt test` for each node in the dependency graph, running
    #   them in the correct order. It also handles seeds and snapshots if present.
    #   A single command replaces what would otherwise be 3–4 separate tasks.
    #
    # If this task fails (model compilation error, SQL error, missing source),
    # Airflow automatically skips dbt_test — broken models are never tested.
    # =========================================================================
    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"dbt build "
            f"--project-dir {DBT_PROJECT_DIR} "
            f"--profiles-dir {DBT_PROFILES_DIR} "
            f"--target {DBT_TARGET}"
        ),
        doc_md=f"""
        ## Task: dbt_build

        **Type**: BashOperator

        Executes all dbt models in dependency order: Bronze → Silver → Gold.

        **Command**: `dbt build --project-dir {DBT_PROJECT_DIR} --profiles-dir {DBT_PROFILES_DIR} --target {DBT_TARGET}`

        **Models**:
        - `staging/stg_github_events` (view)
        - `silver/int_push_events`, `silver/int_pull_requests` (views)
        - `gold/dim_repository`, `gold/dim_contributor` (tables)
        - `gold/fct_github_daily_activity`, `gold/fct_contributor_daily_activity` (tables)

        **Profile**: `pipeone_profile` → target `{DBT_TARGET}` → schema `dbt_{DBT_TARGET}`

        **Failure**: Stops the pipeline — `dbt_test` will not run.
        """,
    )

    # =========================================================================
    # TASK 3 — dbt_test
    # =========================================================================
    # Runs `dbt test` as an explicit, separate validation stage after all models
    # have been built. This is intentionally a separate task (not merged into
    # dbt_build) so that:
    #   1. Test results appear as their own task in the Airflow UI
    #   2. A test failure is visually distinguishable from a build failure
    #   3. Future contributors can add test-specific alerting (Slack, PagerDuty)
    #      by hooking into this task's on_failure_callback
    #
    # Tests run (defined in models/gold/_schema.yml and models/silver/_schema.yml):
    #   - unique + not_null on all primary and surrogate keys
    #   - accepted_values: repo_name, contrib_type, contribution_type
    #   - relationships: FK integrity between fact and dimension tables
    #
    # Hard fail policy:
    #   `dbt test` exits with code 1 if any test fails. BashOperator treats
    #   any non-zero exit code as task failure, which marks the entire DAG run
    #   as FAILED. Broken data never silently passes quality checks.
    # =========================================================================
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"dbt test "
            f"--project-dir {DBT_PROJECT_DIR} "
            f"--profiles-dir {DBT_PROFILES_DIR} "
            f"--target {DBT_TARGET}"
        ),
        doc_md=f"""
        ## Task: dbt_test

        **Type**: BashOperator

        Runs all dbt data quality tests as a hard validation gate.

        **Command**: `dbt test --project-dir {DBT_PROJECT_DIR} --profiles-dir {DBT_PROFILES_DIR} --target {DBT_TARGET}`

        **Tests executed**:
        - `unique` + `not_null` on all PKs and surrogate keys
        - `accepted_values` for repo_name, contrib_type, contribution_type
        - `relationships` (FK integrity) between fact and dimension tables

        **Hard fail**: Any failing test exits with code 1 → task FAILED → DAG FAILED.
        Broken data is never silently accepted downstream.

        **Extending**: Add `on_failure_callback=send_alert` to this task to
        trigger notifications when data quality degrades.
        """,
    )

    # =========================================================================
    # TASK CHAIN
    # =========================================================================
    # Linear dependency — each task must complete successfully before the next
    # one is allowed to start. Airflow enforces this automatically.
    #
    # Failure propagation:
    #   extract_github_events FAILED → dbt_build is SKIPPED → dbt_test is SKIPPED
    #   dbt_build FAILED             → dbt_test is SKIPPED
    #   dbt_test FAILED              → DAG run marked FAILED (no downstream tasks)
    #
    # To extend the pipeline, append tasks after dbt_test:
    #   dbt_test >> notify_slack
    #   dbt_test >> refresh_dashboard
    # =========================================================================
    extract_github_events >> dbt_build >> dbt_test
