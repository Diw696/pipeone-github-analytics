"""
pipeone_pipeline.py — PipeOne Developer Intelligence Platform ELT Pipeline
===========================================================================

Orchestrates the complete ELT pipeline for the PipeOne Developer Intelligence
Platform. Four tasks run in strict linear order; no task is allowed to
start until its predecessor succeeds.

Pipeline Architecture
---------------------

    ┌─────────────────────────────┐     ┌─────────────────────────────┐
    │   GitHub REST API           │     │   Hacker News Firebase API  │
    │   Events endpoint           │     │   Top Stories endpoint      │
    └────────────┬────────────────┘     └────────────┬────────────────┘
                 │                                   │
                 ▼                                   ▼
    ┌─────────────────────────────┐     ┌─────────────────────────────┐
    │  extract_github_events      │     │  extract_hn_stories         │
    │  PythonOperator             │ ─▶  │  PythonOperator             │
    │  → github_events_raw        │     │  → hn_stories_raw           │
    └────────────┬────────────────┘     └────────────┬────────────────┘
                 │                                   │
                 └─────────────────┬───────────────────┘
                                 ▼
                    ┌─────────────────────────────┐
                    │  dbt_build                  │  BashOperator
                    │  Bronze → Silver → Gold     │  13 models
                    └────────────┬────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────────┐
                    │  dbt_test                   │  BashOperator
                    │  Hard data quality gate     │  Fails on any assertion
                    └─────────────────────────────┘

Failure Propagation
-------------------
    extract_github_events FAILED  →  extract_hn_stories SKIPPED → ...
    extract_hn_stories FAILED     →  dbt_build SKIPPED  →  dbt_test SKIPPED
    dbt_build FAILED              →  dbt_test SKIPPED
    dbt_test FAILED               →  DAG run marked FAILED

Environment Variables (injected by docker-compose.yml)
------------------------------------------------------
    GITHUB_TOKEN      — Personal access token for the GitHub REST API
    POSTGRES_HOST     — Hostname of the warehouse service  (= "warehouse")
    POSTGRES_PORT     — PostgreSQL port  (default 5432)
    POSTGRES_DB       — Target database name
    POSTGRES_USER     — Database user
    POSTGRES_PASSWORD — Database password
    DBT_TARGET        — dbt target name; controls which schema dbt writes to
    HN_*              — Hacker News API configuration (see .env.example)

Schedule
--------
    None — manual trigger only. Pipeline runs only when explicitly triggered
    via the Airflow UI, CLI (`airflow dags trigger pipeone_pipeline`), or
    the REST API. To enable daily automation, change `schedule=None` to
    `schedule="@daily"` and review the retry/timeout settings accordingly.

Extending the Pipeline
----------------------
    The linear structure is intentional — new tasks chain cleanly after
    `dbt_test` with zero refactoring:

        dbt_test >> send_slack_notification
        dbt_test >> refresh_metabase_dashboard
        dbt_test >> export_to_bigquery

Maintainers
-----------
    Team:      data-engineering
    Project:   PipeOne — Developer Intelligence Platform
    Airflow:   2.9.x
    dbt Core:  1.x
"""

from datetime import datetime, timedelta

from airflow import DAG
# pyrefly: ignore [missing-import]
from airflow.operators.bash import BashOperator
# pyrefly: ignore [missing-import]
from airflow.operators.python import PythonOperator


# =============================================================================
# PATH CONSTANTS
#
# Module-level strings derived from the volume mounts in docker-compose.yml.
# Centralised here so that a single edit propagates to every dbt command
# without hunting through individual task definitions.
#
# Volume mount → container path mapping:
#   Host: ./dbt_project          →  Container: /opt/airflow/project/dbt_project
#   Host: ./airflow/dbt_profiles →  Container: /home/airflow/.dbt
#
# DBT_TARGET controls which dbt target block (in profiles.yml) is active:
#   "dev"  → writes to schema dbt_dev   (default, safe for local development)
#   "prod" → writes to schema dbt_prod  (production; requires updated profiles.yml)
# =============================================================================
DBT_PROJECT_DIR = "/opt/airflow/project/dbt_project"
DBT_PROFILES_DIR = "/home/airflow/.dbt"
DBT_TARGET = "dev"  # Change to "prod" when promoting to a production environment


# =============================================================================
# DEFAULT ARGUMENTS
#
# Applied to every task in this DAG unless explicitly overridden at the
# individual task level.  Keeping them here (rather than inline inside each
# operator) means a single change propagates to all tasks consistently.
#
# Retry strategy — exponential backoff:
#   Attempt 1 fails → wait 2 min  → Attempt 2
#   Attempt 2 fails → wait 4 min  → Attempt 3
#   Attempt 3 fails → wait 8 min  → Attempt 4 (final)
#   Attempt 4 fails → task marked FAILED permanently
# =============================================================================
# fmt: off  # preserve vertical alignment for readability
default_args = {
    # Displayed in the Airflow UI — identifies who owns this pipeline.
    # Use a team handle or email address in shared Airflow environments.
    "owner": "data-engineering",

    # False: each DAG run is independent and does not wait for the
    # previous run to succeed. This is safe because ingestion is idempotent
    # (ON CONFLICT DO NOTHING) and dbt models are rebuilt from scratch each run.
    "depends_on_past": False,

    # Retry up to 3 times before marking the task as permanently failed.
    # Handles transient errors: GitHub API timeouts, network blips,
    # or a brief PostgreSQL unavailability.
    "retries": 3,

    # Base delay before the first retry attempt.
    # With exponential backoff enabled (below), subsequent delays double:
    #   Attempt 1 → 2 min, Attempt 2 → 4 min, Attempt 3 → 8 min.
    # This covers GitHub's per-minute rate limit resets and short DB blips
    # without holding up the worker for excessively long periods.
    "retry_delay": timedelta(minutes=2),

    # Doubles the retry_delay after each failed attempt.
    # Prevents rapid-fire retries that would exhaust the GitHub API quota again
    # immediately, giving the upstream service time to recover.
    "retry_exponential_backoff": True,

    # Hard ceiling on the retry delay — prevents the backoff from growing
    # unbounded if retries is ever increased without revisiting the delays.
    "max_retry_delay": timedelta(minutes=30),

    # No email alerts (email backend not configured in this environment).
    # In production, set these to True and configure SMTP in Airflow settings.
    # Email notifications require an SMTP backend configured in airflow.cfg
    # (or Airflow's Connections UI). Disabled here because this environment
    # does not have a mail relay.  Enable in production by setting these to
    # True and adding the SMTP connection via the Airflow UI → Admin → Connections.
    "email_on_failure": False,
    "email_on_retry": False,
}
# fmt: on


# =============================================================================
# INGESTION CALLABLE
#
# Defined at module scope (outside the DAG context manager) following Airflow
# best practices:
#   • Module-level callables can be unit-tested without instantiating a DAG.
#   • The Airflow scheduler can import this file and discover the DAG without
#     triggering any side effects (network calls, DB connections, etc.).
#
# Why a wrapper instead of pointing PythonOperator at main() directly?
# -----------------------------------------------------------------------
#   github_client.py calls sys.exit(1) on fatal errors.  sys.exit() raises
#   SystemExit, which Airflow *can* catch but surfaces as a confusing
#   "Process finished with exit code 1" message in the UI — with no context.
#   This thin wrapper intercepts SystemExit and re-raises it as a descriptive
#   RuntimeError that names the three most common root causes, making on-call
#   triage faster without modifying the original ingestion script.
# =============================================================================
# fmt: off
def run_github_ingestion() -> None:
    """
    Thin wrapper that invokes the PipeOne GitHub ingestion entry-point.

    Why deferred import?
    --------------------
    The ``from src.ingestion...`` import is placed *inside* this function
    (not at module level) so that the Airflow scheduler can parse and
    register the DAG file during startup without requiring the ``src/``
    project volume to be mounted yet.  The volume is guaranteed to exist
    by the time this callable is actually *executed* by a worker.

    Why catch SystemExit?
    ---------------------
    ``github_client.main()`` calls ``sys.exit(1)`` on fatal errors.  Airflow
    catches ``SystemExit`` but logs it with a generic message that provides no
    actionable context.  Converting it to ``RuntimeError`` here surfaces the
    three most common root causes directly in the task log, reducing triage
    time without modifying the upstream script.

    Raises
    ------
    RuntimeError
        If the ingestion script terminates with a non-zero exit code,
        indicating a fatal error such as a missing API token, an
        unreachable database, or an unexpected API response.
    """
    try:
        # Deferred import — ``src/`` is on PYTHONPATH=/opt/airflow/project,
        # configured in docker-compose.yml for all Airflow service containers.
        from src.ingestion.github_client import main as ingestion_main

        ingestion_main()

    except SystemExit as exc:
        # sys.exit(0) / sys.exit(None) → normal success path; let it pass.
        # Any other code means the script itself reported a fatal failure.
        if exc.code not in (None, 0):
            raise RuntimeError(
                f"GitHub ingestion script exited with code {exc.code}. "
                "Common causes: missing GITHUB_TOKEN environment variable, "
                "PostgreSQL connection refused, or POSTGRES_PASSWORD not set. "
                "Check the task logs above for the full traceback."
            ) from exc
# fmt: on


# =============================================================================
# HN INGESTION CALLABLE
#
# Mirrors the pattern established by run_github_ingestion() above.
# Defined at module scope for the same reasons: unit-testable without
# instantiating a DAG, and no side effects during scheduler import.
# =============================================================================
# fmt: off
def run_hn_ingestion() -> None:
    """
    Thin wrapper that invokes the PipeOne Hacker News ingestion entry-point.

    Why deferred import?
    --------------------
    Same reason as ``run_github_ingestion``: the ``src/`` project volume
    may not be mounted when the Airflow scheduler first parses this file.
    The deferred import ensures the module is only loaded when a worker
    actually executes this task.

    Why catch SystemExit?
    ---------------------
    ``hn_client.main()`` calls ``sys.exit(1)`` on fatal errors. This wrapper
    converts it to a descriptive ``RuntimeError`` for Airflow's task logs.

    Raises
    ------
    RuntimeError
        If the HN ingestion script terminates with a non-zero exit code.
    """
    try:
        from src.ingestion.hn_client import main as hn_ingestion_main

        hn_ingestion_main()

    except SystemExit as exc:
        if exc.code not in (None, 0):
            raise RuntimeError(
                f"Hacker News ingestion script exited with code {exc.code}. "
                "Common causes: PostgreSQL connection refused, "
                "POSTGRES_PASSWORD not set, or HN API temporarily unavailable. "
                "Check the task logs above for the full traceback."
            ) from exc
# fmt: on


# =============================================================================
# DAG DEFINITION
# =============================================================================
with DAG(
    # The dag_id is the canonical name for this pipeline — it appears in the
    # Airflow UI, REST API responses, CLI output, and log file paths.
    # Changing it after deployment creates a new DAG and orphans run history.
    dag_id="pipeone_pipeline",

    # One-line summary displayed in the Airflow UI DAG list view.
    # Keep it short enough to scan at a glance; full details live in doc_md.
    description=(
        "Multi-source ELT pipeline: GitHub REST API + Hacker News API → "
        "raw PostgreSQL ingestion → dbt Bronze / Silver / Gold → data quality gate."
    ),

    default_args=default_args,

    # Manual trigger only — no cron schedule during development and demo.
    # The pipeline runs exclusively when triggered by one of:
    #   • Airflow UI  → DAG list → Trigger DAG ▶
    #   • Airflow CLI → airflow dags trigger pipeone_pipeline
    #   • REST API    → POST /api/v1/dags/pipeone_pipeline/dagRuns
    # To switch to daily automation: schedule="@daily" (or a cron expression)
    schedule=None,

    # Anchored to the project's first deployment month.
    # A fixed historical date is required by Airflow even when schedule=None.
    # Combined with catchup=False, this guarantees no backfill runs are created
    # if a schedule is ever enabled later.
    start_date=datetime(2026, 7, 1),

    # Do not generate historical DAG runs for the interval between start_date
    # and the current date when this DAG is first activated.
    catchup=False,

    # Allow only one active DAG run at a time.
    # Without this guard, rapid manual triggers could create concurrent runs
    # that write to the same PostgreSQL tables simultaneously, producing
    # row-count anomalies or duplicate-key conflicts in non-idempotent paths.
    max_active_runs=1,

    # Labels used by the Airflow UI filter bar and the REST API.
    tags=["pipeone", "github", "hackernews", "dbt", "elt"],

    # Full documentation rendered in the Airflow UI → DAG detail → Docs tab.
    # Written in Markdown; supports headers, tables, and fenced code blocks.
    doc_md="""
# PipeOne ELT Pipeline

**Project**: PipeOne — GitHub Activity Analytics
**Owner**: data-engineering
**Airflow**: 2.9.x &nbsp;|&nbsp; **dbt Core**: 1.x &nbsp;|&nbsp; **Schedule**: Manual trigger only

---

## Overview

Full ELT pipeline that ingests raw GitHub activity from three high-traffic
open-source repositories, transforms the data through a Bronze → Silver → Gold
medallion architecture using dbt, and enforces data quality with a hard-fail
test gate before any downstream consumer can access the results.

Repositories tracked: `facebook/react`, `microsoft/vscode`, `vercel/next.js`

---

## Pipeline Flow

```
GitHub REST API  (/events endpoint — up to 30 events per repo)
       │
       ▼
extract_github_events   ← PythonOperator
       │   Writes raw JSON payloads to public.github_events_raw (PostgreSQL)
       │   Idempotent: ON CONFLICT (event_id) DO NOTHING
       │
       ▼
dbt_build               ← BashOperator  (dbt build)
       │   Bronze : stg_github_events              (view, type-cast + rename)
       │   Silver : int_push_events                (view, push-event filter)
       │            int_pull_requests              (view, PR-event filter)
       │   Gold   : dim_repository                 (table, repo dimension)
       │            dim_contributor                (table, actor dimension)
       │            fct_github_daily_activity      (table, daily rollup)
       │            fct_contributor_daily_activity (table, per-actor rollup)
       │
       ▼
dbt_test                ← BashOperator  (dbt test)
           Runs uniqueness, not_null, accepted_values, and relationship
           assertions defined in _schema.yml files across Silver and Gold.
           Non-zero exit code → task FAILED → DAG run FAILED.
```

---

## Failure Behaviour

| Task fails | Effect on downstream tasks |
|---|---|
| `extract_github_events` | `dbt_build` and `dbt_test` are **skipped** |
| `dbt_build` | `dbt_test` is **skipped** |
| `dbt_test` | DAG run marked **FAILED** — no downstream tasks exist |

All tasks retry up to **3 times** with **exponential backoff** (2 min → 4 min
→ 8 min) before a permanent failure is recorded.

---

## Trigger Instructions

```bash
# Airflow CLI
airflow dags trigger pipeone_pipeline

# REST API
curl -X POST http://localhost:8080/api/v1/dags/pipeone_pipeline/dagRuns \\
  -H 'Content-Type: application/json' \\
  -u airflow:airflow \\
  -d '{}'
```

---

## Extending the Pipeline

New tasks chain cleanly after `dbt_test` with no refactoring of existing code:

```python
# In the task chain section at the bottom of the DAG file:
dbt_test >> send_slack_notification
dbt_test >> refresh_metabase_dashboard
dbt_test >> export_to_bigquery
```

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `GITHUB_TOKEN` | GitHub Personal Access Token (PAT) for API authentication |
| `POSTGRES_HOST` | PostgreSQL hostname — set to `warehouse` in Docker Compose |
| `POSTGRES_PORT` | PostgreSQL port (default `5432`) |
| `POSTGRES_DB` | Target database name |
| `POSTGRES_USER` | Database user |
| `POSTGRES_PASSWORD` | Database password |
| `DBT_TARGET` | Active dbt target (`dev` → `dbt_dev` schema, `prod` → `dbt_prod`) |
    """,
) as dag:

    # =========================================================================
    # TASK 1 — extract_github_events
    # =========================================================================
    # Invokes the GitHubClient ingestion pipeline via a thin wrapper function.
    # This task does NOT copy or modify any logic inside github_client.py —
    # it simply calls run_github_ingestion(), which in turn calls main().
    #
    # Execution sequence inside the worker process:
    #   1. Authenticate with the GitHub REST API using the GITHUB_TOKEN env var
    #   2. Check remaining API rate limit; abort early if quota is critically low
    #   3. Fetch up to 30 events per repository (3 repos → up to 90 events total)
    #   4. Upsert each event as a raw JSON payload into public.github_events_raw
    #      using psycopg2 — duplicates are silently skipped (ON CONFLICT DO NOTHING)
    #
    # Required environment variables (all injected by docker-compose.yml):
    #   GITHUB_TOKEN      — GitHub PAT; 401 Unauthorized if missing or expired
    #   POSTGRES_HOST     — "warehouse" (the PostgreSQL service name in Compose)
    #   POSTGRES_PORT     — 5432
    #   POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD
    # =========================================================================
    extract_github_events = PythonOperator(
        task_id="extract_github_events",
        python_callable=run_github_ingestion,
        # Guard against a stalled network call or a hung psycopg2 connection.
        # Fetching and inserting 90 events should complete in under 3 minutes
        # under normal conditions.  15 minutes gives generous headroom for
        # slow Docker network start-up on first run, then kills the worker
        # slot if the task genuinely hangs, preventing resource starvation.
        execution_timeout=timedelta(minutes=15),
        doc_md="""
## Task: extract_github_events

**Operator**: `PythonOperator` &nbsp;|&nbsp; **Callable**: `run_github_ingestion`

### Purpose
Ingests recent GitHub activity events for three target repositories and
persists each event as a raw JSON payload in the PostgreSQL warehouse.
This is the **E** (Extract) step of the ELT pipeline.

### Source
| Repository | URL |
|---|---|
| `facebook/react` | https://api.github.com/repos/facebook/react/events |
| `microsoft/vscode` | https://api.github.com/repos/microsoft/vscode/events |
| `vercel/next.js` | https://api.github.com/repos/vercel/next.js/events |

GitHub returns at most **30 events per request** (API maximum), giving
an upper bound of **90 raw events** per pipeline run.

### Destination
Table: `public.github_events_raw` (PostgreSQL warehouse service)

| Column | Description |
|---|---|
| `event_id` | GitHub's unique event ID — primary key |
| `event_type` | e.g. `PushEvent`, `PullRequestEvent` |
| `repo_name` | `owner/repo` string |
| `actor_login` | GitHub username of the event actor |
| `payload` | Full raw JSON payload from the API |
| `created_at` | Event timestamp (UTC) |

### Idempotency
Safe to re-run at any time.  Duplicate events are silently discarded via
`INSERT ... ON CONFLICT (event_id) DO NOTHING` — no row is updated or
duplicated regardless of how many times the task executes.

### Resilience
- **Retries**: 3 attempts with exponential backoff — 2 min → 4 min → 8 min
- **Timeout**: 15 minutes — if exceeded, Airflow raises `AirflowTaskTimeout`,
  marks the task `FAILED`, and frees the worker slot immediately

### Common Failure Causes
| Symptom | Likely cause |
|---|---|
| Exit code 1 — "401 Unauthorized" | `GITHUB_TOKEN` missing or expired |
| Exit code 1 — "Connection refused" | PostgreSQL service not yet healthy |
| Exit code 1 — "rate limit exceeded" | API quota exhausted; retry will recover |
        """,
    )

    # =========================================================================
    # TASK 2 — extract_hn_stories
    # =========================================================================
    # Invokes the HackerNewsClient ingestion pipeline via a thin wrapper.
    #
    # Execution sequence inside the worker process:
    #   1. Fetch the top story ID list from HN Firebase API (no auth needed)
    #   2. Fetch individual story details (up to HN_TOP_STORY_LIMIT stories)
    #   3. Validate each story (must have id and title)
    #   4. Upsert each story into public.hn_stories_raw using psycopg2
    #      ON CONFLICT (story_id) DO UPDATE — refreshes mutable fields
    #
    # Required environment variables:
    #   POSTGRES_HOST / POSTGRES_PORT / POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD
    #   HN_* variables (optional — defaults are in the client)
    # =========================================================================
    extract_hn_stories = PythonOperator(
        task_id="extract_hn_stories",
        python_callable=run_hn_ingestion,
        execution_timeout=timedelta(minutes=15),
        doc_md="""
## Task: extract_hn_stories

**Operator**: `PythonOperator` &nbsp;|&nbsp; **Callable**: `run_hn_ingestion`

### Purpose
Ingests current top stories from Hacker News and persists each story
as a row in the PostgreSQL warehouse. This is the **E** (Extract) step
for the Hacker News data source.

### Source
| API Endpoint | URL |
|---|---|
| Top Stories | https://hacker-news.firebaseio.com/v0/topstories.json |
| Story Detail | https://hacker-news.firebaseio.com/v0/item/{id}.json |

The HN API is public and unauthenticated — no API key required.
Up to **HN_TOP_STORY_LIMIT** stories are fetched per run (default: 50).

### Destination
Table: `public.hn_stories_raw` (PostgreSQL warehouse service)

| Column | Description |
|---|---|
| `story_id` | HN item ID — primary key |
| `title` | Story headline text |
| `author` | HN username of the submitter |
| `url` | External link (NULL for text posts) |
| `score` | Current upvote count (mutable) |
| `time` | Unix timestamp of submission |
| `descendants` | Comment count (mutable) |
| `type` | Item type (story, job, poll) |
| `raw_json` | Complete JSONB payload |
| `fetched_at` | Pipeline ingestion timestamp |

### Idempotency
Safe to re-run. Uses `ON CONFLICT (story_id) DO UPDATE` to refresh
mutable fields (score, descendants) on re-ingestion.

### Resilience
- **Retries**: 3 attempts with exponential backoff
- **Timeout**: 15 minutes
- **Per-request**: Configurable retry + backoff at the HTTP level
        """,
    )

    # =========================================================================
    # TASK 3 — dbt_build
    # =========================================================================
    # Executes `dbt build`, which compiles and materialises all project models
    # in the topological order dictated by their ref() dependency graph:
    #
    #   Bronze layer  (staging)
    #     └─ stg_github_events          view   — type-cast, rename, light cleaning
    #
    #   Silver layer  (intermediate)
    #     ├─ int_push_events            view   — filters PushEvent rows
    #     └─ int_pull_requests          view   — filters PullRequestEvent rows
    #
    #   Gold layer    (serving / analytics)
    #     ├─ dim_repository             table  — one row per tracked repository
    #     ├─ dim_contributor            table  — one row per unique GitHub actor
    #     ├─ fct_github_daily_activity  table  — daily event counts per repo
    #     └─ fct_contributor_daily_activity     — daily contribution counts
    #                                   table    per actor + repo combination
    #
    # Why `dbt build` instead of `dbt run`?
    #   `dbt build` (introduced in dbt 1.0) executes models, seeds, snapshots,
    #   and their associated schema tests in a single, dependency-correct pass.
    #   It replaces the older pattern of chaining `dbt seed → dbt run → dbt test`
    #   as separate Airflow tasks.  One command, one task, full coverage.
    #
    # Failure impact:
    #   A compilation error, SQL error, or missing source relation causes dbt to
    #   exit non-zero.  BashOperator marks the task FAILED and Airflow propagates
    #   the failure — dbt_test is automatically SKIPPED, so broken models are
    #   never promoted or validated against phantom data.
    # =========================================================================
    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"dbt build "
            f"--project-dir {DBT_PROJECT_DIR} "
            f"--profiles-dir {DBT_PROFILES_DIR} "
            f"--target {DBT_TARGET}"
        ),
        # Guard against a zombie dbt process (e.g., PostgreSQL becomes unresponsive
        # after model compilation starts).  Typical wall-clock time for this data
        # volume is under 3 minutes; 30 minutes is a wide safety margin that still
        # ensures the worker slot is reclaimed within a predictable window.
        execution_timeout=timedelta(minutes=30),
        doc_md=f"""
## Task: dbt_build

**Operator**: `BashOperator` &nbsp;|&nbsp; **Command**: `dbt build`

### Purpose
Compiles and materialises all dbt models in dependency order, transforming
raw GitHub event data through the Bronze → Silver → Gold medallion layers.
This is the **T** (Transform) step of the ELT pipeline.

### Command Executed
```bash
dbt build \\
  --project-dir {DBT_PROJECT_DIR} \\
  --profiles-dir {DBT_PROFILES_DIR} \\
  --target {DBT_TARGET}
```

### Model Execution Order

| Layer | Model | Materialisation | Description |
|---|---|---|---|
| Bronze | `stg_github_events` | View | Type-cast and rename raw columns |
| Silver | `int_push_events` | View | Filter push events only |
| Silver | `int_pull_requests` | View | Filter pull request events only |
| Gold | `dim_repository` | Table | Repository dimension |
| Gold | `dim_contributor` | Table | Contributor (actor) dimension |
| Gold | `fct_github_daily_activity` | Table | Daily event counts per repo |
| Gold | `fct_contributor_daily_activity` | Table | Daily counts per actor + repo |

### dbt Profile
- **Profile**: `pipeone_profile` (defined in `{DBT_PROFILES_DIR}/profiles.yml`)
- **Target**: `{DBT_TARGET}` → writes to schema `dbt_{DBT_TARGET}`

### Why `dbt build` and not `dbt run`?
`dbt build` (dbt ≥ 1.0) executes models, seeds, snapshots, **and their inline
schema tests** in a single dependency-ordered pass — replacing the older
`dbt run + dbt test` two-step pattern.  The explicit `dbt_test` task that
follows this one is an *additional* standalone gate, not a replacement.

### Resilience
- **Retries**: Inherited from `default_args` — 3 attempts, exponential backoff
- **Timeout**: 30 minutes — prevents zombie dbt processes from occupying a
  worker slot if the database becomes unresponsive mid-run

### Failure Impact
If this task fails, `dbt_test` is automatically **skipped** by Airflow.
Broken or partially built models are never promoted to the test stage.
        """,
    )

    # =========================================================================
    # TASK 3 — dbt_test
    # =========================================================================
    # Runs `dbt test` as a dedicated, standalone validation stage *after* all
    # models have been successfully built.  Keeping this as a separate Airflow
    # task (rather than relying solely on the inline tests inside `dbt build`)
    # provides three concrete operational benefits:
    #
    #   1. Visibility  — test results appear as a distinct task in the UI,
    #                    making it immediately obvious whether a failure is a
    #                    build problem or a data quality problem.
    #
    #   2. Separation  — the FAILED status of this task signals specifically
    #                    that models built successfully but data did not meet
    #                    quality standards — a meaningful distinction for triage.
    #
    #   3. Extensibility — future on_failure_callback alerting (Slack, PagerDuty,
    #                      email) belongs here, scoped to data quality events
    #                      only, without conflating it with build failures.
    #
    # Test assertions defined in dbt _schema.yml files:
    #   - unique + not_null on all primary keys and surrogate keys
    #   - accepted_values: repo_name, contrib_type, contribution_type columns
    #   - relationships: referential integrity between fact and dimension tables
    #
    # Hard-fail policy:
    #   `dbt test` exits with code 1 if any single assertion fails. BashOperator
    #   surfaces any non-zero exit as a task FAILED, which propagates to the
    #   entire DAG run.  Broken data is never silently accepted by consumers.
    # =========================================================================
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"dbt test "
            f"--project-dir {DBT_PROJECT_DIR} "
            f"--profiles-dir {DBT_PROFILES_DIR} "
            f"--target {DBT_TARGET}"
        ),
        # dbt test executes SQL assertion queries against already-materialised
        # Gold and Silver tables.  Individual tests complete in milliseconds;
        # the 20-minute ceiling exists solely to reclaim the worker slot if
        # a database connection stalls after the test runner has started.
        execution_timeout=timedelta(minutes=20),
        doc_md=f"""
## Task: dbt_test

**Operator**: `BashOperator` &nbsp;|&nbsp; **Command**: `dbt test`

### Purpose
Runs the full suite of dbt schema tests against the materialised Silver and
Gold tables as a hard data quality gate.  This task is the final checkpoint
before the pipeline is considered complete — no downstream consumer should
read from Gold tables in a DAG run where this task has not passed.

### Command Executed
```bash
dbt test \\
  --project-dir {DBT_PROJECT_DIR} \\
  --profiles-dir {DBT_PROFILES_DIR} \\
  --target {DBT_TARGET}
```

### Test Suite

Tests are defined in `_schema.yml` files alongside the dbt models.

| Test type | Applied to | Purpose |
|---|---|---|
| `unique` | All PKs and surrogate keys | No duplicate rows |
| `not_null` | All PKs and surrogate keys | No missing identifiers |
| `accepted_values` | `repo_name`, `contrib_type`, `contribution_type` | Valid enumeration values only |
| `relationships` | Fact → Dimension FK columns | Referential integrity across tables |

### Hard-Fail Policy
`dbt test` exits with code 1 if **any** single assertion fails.  BashOperator
treats any non-zero exit as task `FAILED`, which marks the entire DAG run as
`FAILED`.  Broken data is **never** silently promoted or accepted downstream.

### Resilience
- **Retries**: Inherited from `default_args` — 3 attempts, exponential backoff
- **Timeout**: 20 minutes — kills stalled database connections and frees
  the worker slot

### Extending
To add alerting on data quality failures, attach an `on_failure_callback`
to this task:

```python
def send_quality_alert(context): ...

dbt_test = BashOperator(
    ...,
    on_failure_callback=send_quality_alert,
)
```
        """,
    )

    # =========================================================================
    # TASK CHAIN — linear execution order
    # =========================================================================
    # The >> operator sets a strict sequential dependency: each task must reach
    # state SUCCESS before Airflow schedules the next one.  Any failure or
    # upstream skip stops propagation immediately — nothing runs on bad data.
    #
    # Dependency graph:
    #   extract_github_events  ──►  dbt_build  ──►  dbt_test
    #
    # Failure propagation (Airflow default trigger rule: ALL_SUCCESS):
    #   extract_github_events FAILED  →  dbt_build SKIPPED  →  dbt_test SKIPPED
    #   dbt_build FAILED              →  dbt_test SKIPPED
    #   dbt_test FAILED               →  DAG run FAILED  (no further tasks)
    #
    # To extend the pipeline, chain new tasks after dbt_test:
    #   dbt_test >> notify_slack           # alert when pipeline succeeds
    #   dbt_test >> refresh_dashboard      # trigger a BI tool cache flush
    #   dbt_test >> export_to_bigquery     # forward Gold tables to cloud DW
    # =========================================================================
    extract_github_events >> extract_hn_stories >> dbt_build >> dbt_test
