<h1 align="center">PipeOne</h1>

<p align="center">
  <b>An end-to-end GitHub Analytics data engineering pipeline.</b><br/>
  From raw API events to a fully tested, analytics-ready data warehouse — orchestrated with Apache Airflow.
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://www.getdbt.com/"><img src="https://img.shields.io/badge/dbt-1.7-FF6849?style=flat-square&logo=dbt&logoColor=white" alt="dbt"></a>
  <a href="https://www.postgresql.org/"><img src="https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL"></a>
  <a href="https://airflow.apache.org/"><img src="https://img.shields.io/badge/Airflow-2.9-017CEE?style=flat-square&logo=apacheairflow&logoColor=white" alt="Airflow"></a>
  <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker"></a>
  <img src="https://img.shields.io/badge/Status-Active-22c55e?style=flat-square" alt="Status">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-f59e0b?style=flat-square" alt="License"></a>
</p>

---

## 🔍 What is PipeOne?

PipeOne is a **data engineering portfolio project** that collects live activity data from major open-source GitHub repositories, processes it through a structured data pipeline, and stores analytics-ready results in a warehouse.

**In plain English:** It watches what developers are doing on GitHub — commits, pull requests, code pushes — and organizes that messy raw data into clean, queryable tables you can build dashboards from.

**Repositories tracked:** `facebook/react` · `microsoft/vscode` · `vercel/next.js`

---

## ❓ The Problem

GitHub's Events API returns complex, deeply-nested JSON data. There is no clean, unified view of:
- Which repositories are most active?
- Who are the top contributors this week?
- How many commits happened per day, per project?

Getting answers requires a proper data pipeline — not a one-off script.

---

## ✅ The Solution

A fully automated **ELT pipeline** (Extract → Load → Transform) that:

1. **Extracts** raw event data from the GitHub REST API
2. **Loads** it into PostgreSQL as raw JSON
3. **Transforms** it through three structured layers (Bronze → Silver → Gold)
4. **Tests** data quality at every stage
5. **Orchestrates** everything automatically with Apache Airflow

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      DATA SOURCES                            │
│          GitHub REST API — Events Endpoint                   │
│    facebook/react · microsoft/vscode · vercel/next.js        │
└────────────────────────┬─────────────────────────────────────┘
                         │  JSON (up to 90 events per repo)
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                  PYTHON INGESTION                            │
│         src/ingestion/github_client.py                       │
│         Writes raw JSON → public.github_events_raw           │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│               POSTGRESQL WAREHOUSE (Docker)                  │
│              Raw JSONB storage — preserved as-is             │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                   dbt BUILD (7 models)                       │
│  ┌─────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │   BRONZE    │→ │     SILVER       │→ │      GOLD      │  │
│  │  (Staging)  │  │ (Intermediate)   │  │  (Analytics)   │  │
│  └─────────────┘  └──────────────────┘  └────────────────┘  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                   dbt TEST (Quality Gate)                    │
│         Fails the pipeline if any assertion breaks           │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              STREAMLIT DASHBOARD  (Next Phase)               │
│         Reads exclusively from the Gold layer                │
└──────────────────────────────────────────────────────────────┘
```

**The entire pipeline is orchestrated by Apache Airflow** — one trigger runs everything in the correct order with automatic failure propagation.

---

## ⚙️ Technology Stack

| Layer | Tool | Why |
|---|---|---|
| **Ingestion** | Python 3.11 + `requests` | Fetches events from GitHub REST API |
| **Storage** | PostgreSQL 15 | Stores raw JSONB and transformed tables |
| **Transformation** | dbt Core 1.7 | SQL-based Medallion Architecture |
| **Orchestration** | Apache Airflow 2.9 | Schedules and sequences all pipeline tasks |
| **Containers** | Docker Compose | One-command reproducible local environment |
| **Visualization** | Streamlit *(upcoming)* | Analytics dashboard on the Gold layer |

---

## 🔄 Pipeline Flow (Airflow DAG)

Three tasks run in strict sequence. If one fails, all downstream tasks are skipped automatically.

```
extract_github_events  ──►  dbt_build  ──►  dbt_test
   (PythonOperator)        (BashOperator)   (BashOperator)
```

| Task | What it does |
|---|---|
| `extract_github_events` | Calls the GitHub API, writes raw JSON to `github_events_raw` |
| `dbt_build` | Runs all 7 dbt models: Bronze → Silver → Gold |
| `dbt_test` | Runs all data quality assertions — fails the DAG if any break |

> **Failure propagation:** If `dbt_build` fails, `dbt_test` is skipped. If `extract_github_events` fails, both downstream tasks are skipped.

> **DAG schedule:** Manual trigger only (`schedule=None`). Change to `@daily` for automated runs.

---

## 🏅 Medallion Architecture

The Medallion Architecture organizes data into three quality tiers, making it progressively cleaner and more useful at each stage.

### 🥉 Bronze — Raw Staging
> *"Store it exactly as received."*

- **Model:** `stg_github_events`
- Ingests raw JSONB from PostgreSQL, adds `fetched_at` timestamp
- Preserves the original nested payload for full re-runnability
- Nothing is dropped or changed at this stage

### 🥈 Silver — Cleaned & Structured
> *"Unpack and normalize the data."*

- **Models:** `int_push_events` · `int_pull_requests`
- Flattens nested JSON using PostgreSQL operators (`->`, `->>`)
- Separates events by type (push vs. pull request)
- Adds operational metrics and standardized field names

### 🥇 Gold — Analytics Ready
> *"Answer business questions directly."*

- **Models:** 4 tables — dimensions + facts (Star Schema)
- Pre-aggregated and optimized for dashboards
- MD5 surrogate keys enforce referential integrity
- This is the layer Streamlit will query

---

## 📊 Gold Layer — Star Schema

The Gold layer follows a **Star Schema** — dimensions describe *who/what*, facts describe *what happened*.

| Model | Type | Description |
|---|---|---|
| `dim_repository` | Dimension | Repository metadata — name, language, owner, org |
| `dim_contributor` | Dimension | Developer directory — deduplicated contributor profiles |
| `fct_github_daily_activity` | Fact | Daily snapshot of commit counts and push events per repo |
| `fct_contributor_daily_activity` | Fact | Daily contribution breakdown by developer, repo, and action type |

---

## 🧪 Data Quality

dbt tests run automatically after every build. The pipeline **fails hard** if any test breaks — bad data never reaches the Gold layer.

| Test Type | What it checks |
|---|---|
| `unique` | No duplicate surrogate keys |
| `not_null` | Critical fields are always populated |
| `relationships` | Fact table foreign keys match dimension tables |
| `accepted_values` | Categorical fields only contain valid values |
| Custom SQL tests | No negative commit counts, no future timestamps |

---

## 📁 Project Structure

```
pipeone/
│
├── airflow/
│   ├── dags/
│   │   └── pipeone_pipeline.py     # Main Airflow DAG (3 tasks)
│   ├── dbt_profiles/               # dbt connection profiles for Airflow
│   └── Dockerfile                  # Airflow container config
│
├── dbt_project/
│   └── models/
│       ├── staging/                # 🥉 Bronze: stg_github_events
│       ├── silver/                 # 🥈 Silver: int_push_events, int_pull_requests
│       └── gold/                   # 🥇 Gold: dim_repository, dim_contributor,
│                                   #          fct_github_daily_activity,
│                                   #          fct_contributor_daily_activity
│
├── src/
│   ├── ingestion/
│   │   └── github_client.py        # GitHub API client
│   ├── database/
│   │   └── init_db.py              # PostgreSQL schema setup
│   └── dashboard/                  # Streamlit dashboard (next phase)
│
├── docs/
│   └── roadmap_3rd_year.md         # Long-term vision document
│
├── docker-compose.yml              # Spins up PostgreSQL + Airflow
├── requirements.txt
└── .env.example                    # Environment variable template
```

---

## 🚀 Getting Started

### Prerequisites
- Docker Desktop installed and running
- A GitHub Personal Access Token (PAT)

### 1. Clone & Configure

```bash
git clone https://github.com/Diw696/pipeone-github-analytics.git
cd pipeone-github-analytics

# Set up environment variables
cp .env.example .env
# Edit .env — add your GITHUB_TOKEN
```

### 2. Start the Infrastructure

```bash
docker-compose up -d
```

This starts PostgreSQL and Apache Airflow. Airflow UI available at **http://localhost:8080**.

### 3. Initialize the Database

```bash
python src/database/init_db.py
```

### 4. Run the Pipeline

**Option A — Via Airflow UI (recommended):**
1. Go to `http://localhost:8080`
2. Find the `pipeone_pipeline` DAG
3. Click **Trigger DAG ▶**

**Option B — Manual run:**
```bash
python src/ingestion/github_client.py

cd dbt_project
dbt run
dbt test
```

### 5. Explore the Data

```bash
cd dbt_project
dbt docs generate
dbt docs serve
# Open http://localhost:8080 to browse model lineage and documentation
```

---

## 📍 Current Status

| Milestone | Status |
|---|---|
| GitHub API Ingestion | ✅ Complete |
| PostgreSQL Raw Storage | ✅ Complete |
| Bronze Layer (dbt staging) | ✅ Complete |
| Silver Layer (dbt intermediate) | ✅ Complete |
| Gold Layer (Star Schema) | ✅ Complete |
| Data Quality Tests | ✅ Complete |
| Apache Airflow Orchestration | ✅ Complete |
| Streamlit Analytics Dashboard | ⏳ **In Progress** |

---

## 🗺️ Roadmap

| Phase | Goal |
|---|---|
| **Now** | Streamlit dashboard — querying the Gold layer directly |
| **Next** | Incremental dbt models (only process new data) |
| **Later** | Cloud migration — Snowflake or BigQuery |
| **Future** | Streaming ingestion with Apache Kafka |
| **Future** | ML models — contributor churn prediction, repo health scoring |

Full roadmap: [`docs/roadmap_3rd_year.md`](docs/roadmap_3rd_year.md)

---

## 🎓 What I Learned

Building PipeOne covered real-world data engineering from end to end:

- **ELT design** — why you load first, then transform inside the warehouse
- **JSONB handling** — flattening deeply nested API responses with PostgreSQL operators
- **Dimensional modeling** — building a Star Schema (Facts + Dimensions)
- **dbt fundamentals** — models, tests, macros, and materialization strategies
- **Airflow orchestration** — DAGs, task dependencies, and failure propagation
- **Docker networking** — wiring Airflow, dbt, and PostgreSQL inside containers
- **Data quality automation** — treating testing as a first-class pipeline concern

---

## 💡 Why This Project Matters

Most data engineering tutorials show one piece of the puzzle.

PipeOne connects them all — ingestion, storage, transformation, testing, and orchestration — in a single project that mirrors how real data teams work.

> It's not a toy script. It's a pattern you'd recognize in a production data engineering team.

---

## 👤 Author

**Diwakar Kaushik**  
CSE — Data Engineering & AI · Lovely Professional University

📧 devkaushik6906@gmail.com · 🐙 [@Diw696](https://github.com/Diw696)

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.