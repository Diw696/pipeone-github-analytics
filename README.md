Markdown# PipeOne

**A data engineering platform demonstrating end-to-end GitHub analytics using ELT patterns, dimensional modeling, and the Medallion Architecture.**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![dbt](https://img.shields.io/badge/dbt-1.7.4-FF6849.svg)](https://www.getdbt.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![GitHub API](https://img.shields.io/badge/GitHub-Events_API-181717.svg)](https://docs.github.com/en/rest/activity/events)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Project Overview

PipeOne is an enterprise-grade data platform that ingests live GitHub events from major open-source repositories (`facebook/react`, `microsoft/vscode`, `vercel/next.js`), transforms them through a structured Medallion Architecture, and ensures data quality with automated testing boundaries.

* **The Problem:** Organizations tracking engineering velocity across diverse open-source ecosystems face extreme telemetry fragmentation. Data payloads are deep, nested, and constantly shifting.
* **The Solution:** A robust, automated ELT pipeline that captures real-time GitHub event streams, stores them durably in PostgreSQL binary JSONB blocks, uses dbt Core to unpack payloads into an optimized analytical Star Schema, and programmatically validates processing integrity.
* **Why This Matters:** This portfolio piece demonstrates production data engineering patterns: idempotent ingestion design, in-warehouse JSON flattening, declarative structural data transformations, and comprehensive referential test assertions.

---

## Current Status

✅ Week 1: Infrastructure, API Ingestion & Raw JSONB Storage✅ Week 2: Medallion Bronze & Silver Transformations✅ Week 3: Gold Analytical Warehouse (Star Schema & Business Marts)⏳ Week 4: Dashboard Visualization & Final Presentation (Accelerated Sprint)
**Key Execution Capabilities:**
* **Pipeline Integrity:** Integrated automated schema assertions, singular business rules, and foreign key validations across all execution blocks.
* **Warehouse Engine:** Pushes compute down to PostgreSQL 15, optimizing storage overhead via localized views and high-performance materialized tables.
* **Code Standard:** Fully version-controlled, modularized via Common Table Expressions (CTEs), and self-documenting.

---

## Architecture

     GitHub Events API
             │
             ▼
      Python Ingestion
             │
             ▼
   PostgreSQL Warehouse
 [github_events_raw (JSONB)]
             │
             ▼
        dbt Bronze
   [stg_github_events]
             │
             ▼
        dbt Silver
int_push_events      int_pull_requests
│                       │
└───────────┬───────────┘
│
▼
dbt Gold
┌───────────┼───────────┬──────────────────────┐
▼           ▼           ▼                      ▼
dim_repository dim_contributor fct_github_daily fct_contributor_daily
│           │           │                      │
└───────────┼───────────┴──────────────────────┘
│
▼
Automated Data Quality Suite
│
▼
---

## Medallion Architecture Specification

### 🥉 Bronze Layer (Staging)
* **Objective:** Direct ingestion passthrough tracking.
* **Model:** `stg_github_events`
* **Transformations:** Enforces timestamp standardization (`fetched_at`) and metadata categorization while preserving the original raw nested `JSONB` tree exactly as received for complete re-runnability.

### 🥈 Silver Layer (Intermediate Processing)
* **Objective:** Relational transformation and business type separation.
* **Models:** `int_push_events`, `int_pull_requests`
* **Transformations:** Flattens complex JSON arrays using native PostgreSQL relational operators (`->` and `->>`), structures event-specific variables, and establishes foundational operational metrics[cite: 2, 3].

### 🥇 Gold Layer (Analytics Warehouse)
* **Objective:** Enterprise Star Schema optimized for downstream visualization tools.
* **Models:** 
  * `dim_repository`: Master dimension classifying organization ownership, primary code languages, and base repository metadata.
  * `dim_contributor`: Unified developer directory tracking deduplicated individual contributions and behavioral segmentation profiles.
  * `fct_github_daily_activity`: Pre-computed daily snapshot aggregation of aggregate commit weights, push cycles, and PR events per repository.
  * `fct_contributor_daily_activity`: Granular transactional fact tracking precise daily contributions grouped by developer, repository, and action type.
* **Transformations:** Implements deterministic `md5()` surrogate hashing keys to enforce structural referential integrity and isolates query logic from visualization layers.

---

## Project Structure

pipeone-github-analytics/
│
├── src/
│   ├── ingestion/
│   │   ├── github_client.py            # API ingestion engine
│   │   └── init.py
│   └── database/
│       ├── init_db.py                  # Raw database schema initialization
│       └── init.py
│
├── dbt_project/                        # Core transformation layer
│   ├── dbt_project.yml                 # dbt project configurations
│   ├── profiles.yml.example            # Connection infrastructure template
│   ├── setup_dbt_profile.ps1           # Deployment script automation
│   ├── models/
│   │   ├── staging/
│   │   │   ├── _sources.yml            # Source definitions and data fresh checks
│   │   │   └── stg_github_events.sql   # Bronze layer passthrough view[cite: 1]
│   │   ├── silver/
│   │   │   ├── _schema.yml             # Intermediate column validation suite
│   │   │   ├── int_push_events.sql     # Flattened PushEvent view logic
│   │   │   └── int_pull_requests.sql   # Flattened PullRequestEvent view logic
│   │   └── gold/
│   │       ├── _schema.yml             # Star Schema referential integrity tests
│   │       ├── dim_repository.sql      # Repository context table
│   │       ├── dim_contributor.sql     # Unified developer profile dimension
│   │       ├── fct_github_daily_activity.sql     # Repository daily analytics mart[cite: 2]
│   │       ├── fct_contributor_daily_activity.sql # Individual user contribution metrics[cite: 1]
│   └── tests/
│       ├── no_future_timestamps.sql    # Custom business rule assertion
│       ├── push_model_integrity.sql    # Payload schema consistency validation
│       └── no_negative_commit_count.sql # Mathematical boundary validation
│
├── docker-compose.yml                  # Localized warehouse containerization
├── requirements.txt                    # Python application environment blocks
└── README.md  
---

## Tech Stack

| Component | Tool | Core Engineering Purpose |
| :--- | :--- | :--- |
| **Language** | Python 3.11 + SQL | High-speed data fetching matched with declarative analytical computing. |
| **API layer** | GitHub Events API | Real-time, complex public event telemetry streams. |
| **Warehouse** | PostgreSQL 15 | Heavy-duty transaction processing with robust raw `JSONB` data parsing support. |
| **Containers** | Docker Compose | Isolated, highly reproducible development infrastructure environments. |
| **Orchestration** | dbt Core | Directed Acyclic Graph (DAG) dependency mapping, documentation, and asset testing. |

---

## Data Quality & Test Automation

The pipeline features a continuous data validation framework deployed across all layer interfaces:
* **Structural Schema Assertions:** `unique` and `not_null` constraints applied to surrogate hash elements to eliminate structural entry corruption.
* **Referential Integrity Validation:** Automatic `relationships` validations mapping fact foreign keys directly to corresponding dimension tables, blocking orphans.
* **Categorical Boundary Rules:** `accepted_values` checks guaranteeing field data consistency (e.g., contribution work classification tags).
* **Singular Business Rules:** Custom isolated SQL scripts testing complex constraints like preventing negative integer logs and dropping impossible future timestamps.

---

## Quick Start & Verification

### Setup Infrastructure
```bash
# Clone the workspace
git clone [https://github.com/Diw696/pipeone-github-analytics.git](https://github.com/Diw696/pipeone-github-analytics.git)
cd pipeone-github-analytics

# Deploy environment variables
cp .env.example .env

# Spin up the container database
docker-compose up -d

# Trigger Python extraction payload scripts
python src/database/init_db.py
python src/ingestion/github_client.py
Compile & Test the Analytics SchemaBashcd dbt_project

# Run the transformation models
dbt run

# Execute the complete validation test block
dbt test

Interactive Documentation Lookups

Bash

dbt docs generate
dbt docs serve
Navigate to http://localhost:8000 inside your browser to view interactive dependency lineages, field mappings, and compile models live.

Next Steps & Roadmap

    Visualization Integration: Connect an analytical interface layer (Streamlit) directly to the physical Gold layer warehouse tables.

    Metric Engineering: Construct dashboard interface visuals tracing rolling code merge frequencies, daily commits, and active contributor ranks.

Author

Diwakar Kaushik

CSE Data Engineering & AI Student | Lovely Professional University

    📧 devkaushik6906@gmail.com

License

MIT License - see LICENSE file for details.


---
