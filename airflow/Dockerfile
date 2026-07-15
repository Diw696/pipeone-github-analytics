# =============================================================================
# PipeOne — Custom Airflow Docker Image
# =============================================================================
#
# Base image: Official Apache Airflow 2.9.3 with Python 3.11
# Source:     https://hub.docker.com/r/apache/airflow
#
# Purpose:
#   The official Airflow base image does not include project-specific
#   dependencies like dbt-postgres, requests, or psycopg2. This Dockerfile
#   extends the base image and installs all packages from the project's
#   requirements.txt, producing a single reproducible image used by:
#     - airflow-init     (DB migration + user creation)
#     - airflow-webserver (Airflow UI)
#     - airflow-scheduler (task execution)
#
# Why not install at container startup?
#   Installing packages at startup is slow, non-reproducible, and can fail
#   silently. Baking dependencies into the image ensures all three Airflow
#   services are always identical.
#
# Build:
#   Docker Compose handles building automatically via the 'build:' key.
#   To rebuild manually after changing requirements.txt:
#     docker compose build --no-cache
# =============================================================================

FROM apache/airflow:2.9.3-python3.11

# Switch to the 'airflow' user (required — Airflow base image enforces this).
# Running as root would cause permission errors with Airflow's internal checks.
USER airflow

# ---------------------------------------------------------------------------
# Install project Python dependencies
#
# We copy requirements.txt from the project root (build context = project root).
# Docker caches this layer — if requirements.txt is unchanged, pip is skipped
# on subsequent builds, making rebuilds fast.
# ---------------------------------------------------------------------------
COPY --chown=airflow:root requirements.txt /tmp/project_requirements.txt

RUN pip install --no-cache-dir -r /tmp/project_requirements.txt

# ---------------------------------------------------------------------------
# Working directory
# The DAG's BashOperators will cd into the dbt_project directory explicitly,
# so the working directory here is set to Airflow's standard location.
# ---------------------------------------------------------------------------
WORKDIR /opt/airflow
