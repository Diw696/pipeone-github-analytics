# PipeOne

**A data engineering project demonstrating end-to-end GitHub analytics using ELT patterns and the Medallion Architecture.**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![dbt](https://img.shields.io/badge/dbt-1.7.4-FF6849.svg)](https://www.getdbt.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![GitHub API](https://img.shields.io/badge/GitHub-Events_API-181717.svg)](https://docs.github.com/en/rest/activity/events)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Project Overview

PipeOne is a complete data platform that ingests live GitHub events from major open-source repositories, transforms them through a structured medallion architecture, and ensures data quality with automated tests.

**The Problem:** Organizations tracking developer activity across multiple GitHub repositories face fragmentation. Data lives in separate places with no unified view.

**The Solution:** An automated ELT pipeline that continuously captures GitHub events, stores them durably in PostgreSQL,transforms raw GitHub event data into analytics-ready relational models using dbt, and validates everything with automated tests.

**Why This Matters:** This project demonstrates production data engineering patterns: idempotent loading, JSONB handling, declarative transformations, and data quality validation—all critical for real-world analytics platforms.

---

## Current Status

```
✅ Week 1: API Ingestion & Raw Storage
✅ Week 2: Bronze & Silver Layers + Data Quality Tests (26/26 PASSING)
🟡 Week 3: Gold Layer (Planned)
⚪ Week 4: Dashboard & Deployment (Planned)
```

**Key Metrics:**
- **Data Quality:** PASS=26, WARN=0, ERROR=0
- **Models Built:** 1 source, 3 models, 26 tests
- **Test Coverage:** Schema tests, business validations, source tests
- **Code Quality:** Version controlled, documented, tested

---

## Architecture

GitHub Events API
        │
        ▼
Python (Extract + Load)
        │
        ▼
PostgreSQL
github_events_raw (JSONB)
        │
        ▼
dbt Bronze
(stg_github_events)
        │
        ▼
dbt Silver
(int_push_events / int_pull_requests)
        │
        ▼
Automated Data Quality Tests
        │
        ▼
Analytics-Ready Data

---

## Medallion Architecture

**Bronze Layer**
- Raw data from GitHub API stored as-is in JSONB format
- Single table: `stg_github_events`
- No transformations—preserves original structure for debugging
- Enables flexible querying without schema changes

**Silver Layer**
- Structured, event-specific transformations
- Two models: `int_push_events`, `int_pull_requests`
- JSONB parsed into clean relational columns
- Ready for downstream analysis
- Includes Automated Data Quality Framework

**Gold Layer**
- **Status:** Not yet implemented
- Planned for Week 3: aggregated metrics, fact tables, dimension tables
- Will be optimized for dashboard and reporting queries

┌──────────────────────────────────────────────────────────────┐
│           pipeone_warehouse (PostgreSQL Database)            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  public schema                                               │
│  ┌──────────────────────────────────────────────┐            │
│  │ github_events_raw (Table)                    │            │
│  │ Raw Landing Table (JSONB)                    │            │
│  └──────────────────┬───────────────────────────┘            │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────┐            │
│  │ stg_github_events (View)                     │            │
│  │ Bronze Layer                                 │            │
│  │ • Source mapping                             │            │
│  │ • Timestamp standardization                  │            │
│  │ • Preserve raw JSONB                         │            │
│  └──────────────────┬───────────────────────────┘            │
│                     │                                        │
│          ┌──────────┴──────────┐                             │
│          ▼                     ▼                             │
│  ┌─────────────────┐   ┌────────────────────┐               │
│  │ int_push_events │   │ int_pull_requests  │               │
│  │ Silver Layer    │   │ Silver Layer       │               │
│  │ • Push metrics  │   │ • PR metrics       │               │
│  │ • Flat schema   │   │ • Flat schema      │               │
│  └─────────────────┘   └────────────────────┘               │
│                                                              │
└──────────────────────────────────────────────────────────────┘

---

## Project Structure

```
pipeone-github-analytics/
│
├── src/
│   ├── ingestion/
│   │   ├── github_client.py          # GitHub API integration
│   │   └── __init__.py
│   └── database/
│       ├── init_db.py                # Schema initialization
│       └── __init__.py
│
├── dbt_project/                      # dbt transformation project
│   ├── dbt_project.yml               # dbt configuration
│   ├── profiles.yml.example          # Connection template
│   ├── setup_dbt_profile.ps1         # Profile automation
│   ├── models/
│   │   ├── staging/
│   │   │   ├── _sources.yml          # Source definitions + auto-tests
│   │   │   └── stg_github_events.sql # Bronze passthrough view
│   │   └── silver/
│   │       ├── int_push_events.sql   # PushEvent transformation
│   │       ├── int_pull_requests.sql # PullRequestEvent transformation
│   │       └── _schema.yml           # Schema & column tests
│   ├── tests/
│   │   ├── no_future_timestamps.sql       # Business validation
│   │   ├── push_model_integrity.sql       # Event type validation
│   │   └── no_negative_commit_count.sql   # Data quality check
│   └── logs/
│       └── dbt.log                   # Execution logs
│
├── docs/
│   ├── design_doc.md                 # Architecture & design decisions
│   ├── week1/WEEK1_SUBMISSION.md     # Week 1 deliverable
│   └── week2/
│       ├── WEEK2_ARCHITECTURE.md
│       ├── WEEK2_DAY1_SUMMARY.md
│       ├── WEEK2_DAY2_BRONZE_LAYER.md
│       ├── WEEK2_DAY3_SILVER_LAYER.md
│       └── WEEK2_DAY4_TESTING.md
│
├── .env                              # Secrets (not committed)
├── .env.example                      # Template
├── .gitignore
├── docker-compose.yml                # PostgreSQL container
├── requirements.txt                  # Python dependencies
├── test_database.py                  # Connection verification
├── verify_pipeline.py                # Data verification
└── README.md
```

---

## Tech Stack

| Component | Tool | Why |
|-----------|------|-----|
| **Language** | Python + SQL | Best tools for their jobs |
| **API** | GitHub Events API | Real-time, public, well-documented |
| **Database** | PostgreSQL | Powerful, free, excellent JSON support |
| **Containers** | Docker Compose | Reproducible local setup |
| **Transform** | dbt | Dependency tracking, testing, documentation |
| **Version Control** | Git + GitHub | Essential for collaboration |

---

## ELT Pipeline

This project uses **ELT** (Extract → Load → Transform) instead of ETL:

- **Extract:** Python fetches events from GitHub API
- **Load:** Raw JSON stored immediately in PostgreSQL (preserves original structure)
- **Transform:** dbt transforms data into business models (SQL in version control)

**Why ELT?**
- Preserve raw data for debugging and re-transformation
- Transform logic stays in version control (SQL)
- Easy to re-run transformations without re-ingesting
- Cost-effective: leverage database compute power
- Scales better than ETL for data volumes

---

## Data Quality

**26 Automated Tests Currently**

| Type | Count | Purpose |
|------|-------|---------|
| Schema Tests | 13 | Unique, not-null, accepted-values on key columns |
| Singular Tests | 3 | Business rules: no future timestamps, no negative counts, event type validation |
| Source Tests | 6 | Auto-generated source freshness and relationship tests |
| **Total** | **26** | **PASS=26, WARN=0, ERROR=0** |

**Why Testing Matters:**
- Catches data quality issues before they reach dashboards
- Developers can refactor with confidence
- Production data is always trustworthy
- Tests run automatically on every build

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- GitHub Personal Access Token ([generate here](https://github.com/settings/tokens) with `public_repo` scope)

### Setup

```bash
# Clone repository
git clone https://github.com/Diw696/pipeone-github-analytics.git
cd pipeone-github-analytics

# Create environment file
cp .env.example .env

# Edit .env with your credentials:
# GITHUB_TOKEN=your_token_here
# POSTGRES_PASSWORD=your_password
# DB_NAME=github_analytics
```

### Week 1: Ingestion & Storage

```bash
# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL
docker-compose up -d

# Initialize database
python src/database/init_db.py

# Test connection
python test_database.py

# Ingest GitHub events
python src/ingestion/github_client.py

# Verify data
python verify_pipeline.py
```

### Week 2: Transformation & Testing

```bash
# Navigate to dbt project
cd dbt_project

# Configure dbt profile (Windows PowerShell)
.\setup_dbt_profile.ps1

# Or manually edit profiles.yml with your PostgreSQL credentials

# Parse models
dbt parse

#Verification 
dbt debug

# Build Bronze & Silver layers
dbt run

# Execute all tests
dbt test

# Or run both at once
dbt build
```

### Expected Output

```
Running with dbt=1.7.4
Found 3 models, 26 tests, 1 source, 0 exposures

Building...
Completed successfully

Done. PASS=26 WARN=0 ERROR=0 SKIP=0 TOTAL=26
```

### Verify Results

```bash
# Generate and view dbt docs
dbt docs generate
dbt docs serve  # Visit http://localhost:8000

# Or query PostgreSQL directly
psql -U postgres -d github_analytics

# Inside psql:
SELECT * FROM stg_github_events LIMIT 5;
SELECT * FROM int_push_events LIMIT 5;
SELECT * FROM int_pull_requests LIMIT 5;
```

---

## Key Learnings

**Week 1: API to Warehouse**
- GitHub Events API structure and rate limiting
- PostgreSQL JSONB for flexible schema storage
- Idempotent pipelines (PRIMARY KEY + ON CONFLICT DO NOTHING)
- Docker Compose for local reproducibility

**Week 2: Transform with dbt**
- JSONB operators (`->`, `->>`, `jsonb_array_length()`)
- dbt `ref()` for dependency tracking and lineage
- dbt source definitions and auto-generated tests
- Schema tests vs. singular (custom) tests
- Materialization choices (VIEW vs TABLE)

**Data Quality & Testing**
- Catching issues before they reach dashboards
- Schema tests for fast validation
- Custom SQL tests for business rules
- Test failures as clues, not blockers

---

## Design Decisions

**Why PostgreSQL JSONB?**
- Bronze (Week 1): Store GitHub's nested JSON as-is for flexibility
- Silver (Week 2): Parse into relational columns for analysis
- Three-layer approach: flexibility (raw) → structure (transform) → performance (aggregate)

**Why Medallion Architecture?**
- Bronze: Single source of truth (raw, unmodified)
- Silver: Clean, business-specific models ready for analysis
- Gold: Aggregated, optimized for dashboards (not yet built)
- Each layer independently queryable, interconnected via dbt dependencies

**Why dbt?**
- SQL is the analytics standard
- Automatic dependency tracking and build ordering
- Testing and documentation built-in
- Easy to refactor and version control transformations

---

## Roadmap


🥇 Gold Layer

📊 Dashboard

☁ Deployment

⚡ CI/CD


## Author

**Diwakar Kaushik**  
CSE Data Engineering & AI Student | Lovely Professional University

- 📧 [devkaushik6906@gmail.com](mailto:devkaushik6906@gmail.com)
- 💼 [LinkedIn](https://www.linkedin.com/in/diwakar-kaushik-a40b65310/)
- 🐙 [GitHub](https://github.com/Diw696)

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

