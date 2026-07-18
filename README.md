<h1 align="center">PipeOne — Developer Intelligence Platform</h1>

<p align="center">
  <b>A multi-source developer signals intelligence platform.</b><br/>
  Inquests live activity from GitHub APIs and community discussions from Hacker News, transforming them through a dbt Medallion Architecture orchestrated by Apache Airflow.
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://www.getdbt.com/"><img src="https://img.shields.io/badge/dbt-1.7-FF6849?style=flat-square&logo=dbt&logoColor=white" alt="dbt"></a>
  <a href="https://www.postgresql.org/"><img src="https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL"></a>
  <a href="https://airflow.apache.org/"><img src="https://img.shields.io/badge/Airflow-2.9-017CEE?style=flat-square&logo=apacheairflow&logoColor=white" alt="Airflow"></a>
  <a href="https://streamlit.io/"><img src="https://img.shields.io/badge/Streamlit-1.36-FF4B4B?style=flat-square&logo=streamlit&logoColor=white" alt="Streamlit"></a>
  <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker"></a>
  <img src="https://img.shields.io/badge/Status-Active-22c55e?style=flat-square" alt="Status">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-f59e0b?style=flat-square" alt="License"></a>
</p>

---

## 🔍 What is PipeOne?

PipeOne is an end-to-end data platform that gathers developer activity events and community discussion signals across major open-source ecosystems.

By combining direct version control signals (GitHub pushes, pull requests, commits) with community discussions (Hacker News stories, upvotes, comments), PipeOne provides **cross-source analytics** to measure open-source traction, community interest, and developer velocity.

**Monitored Repositories:**
*   `facebook/react` (JavaScript UI library)
*   `microsoft/vscode` (TypeScript code editor)
*   `vercel/next.js` (JavaScript full-stack framework)

---

## 🏗️ System Architecture

```
                               DATA SOURCES
           GitHub REST API                      Hacker News Firebase API
     (Events: push, pull request)               (Top Stories, item details)
                  │                                         │
                  ▼                                         ▼
            INGESTION CLIENT                          INGESTION CLIENT
     (src/ingestion/github_client.py)           (src/ingestion/hn_client.py)
                  │                                         │
                  └────────────────────┬────────────────────┘
                                       ▼
                       POSTGRESQL CENTRAL WAREHOUSE
                  (github_events_raw / hn_stories_raw)
                                       │
                                       ▼
                         dbt MEDALLION TRANSFORMATIONS
     ┌──────────────────────┬────────────────────────┬─────────────────────┐
     │  🥉 BRONZE (Staging) │   🥈 SILVER (Intermed) │  🥇 GOLD (Serving)  │
     │   stg_github_events  │   int_push_events      │   dim_repository    │
     │   stg_hn_stories     │   int_pull_requests    │   dim_contributor   │
     │                      │   int_hn_stories       │   dim_hn_story      │
     │                      │   int_hn_repo_mentions │   fct_github_*      │
     │                      │                        │   fct_hn_*          │
     └──────────────────────┴────────────────────────┴─────────────────────┘
                                       │
                                       ▼
                            dbt DATA QUALITY GATE
                  (128 assertions checking schema + rules)
                                       │
                                       ▼
                       APACHE AIRFLOW ORCHESTRATION
             (Linear Dag: GitHub Ingest -> HN Ingest -> build -> test)
                                       │
                                       ▼
                          STREAMLIT ANALYTICS CONSOLE
                  (Executive Console querying tested Gold Layer)
```

---

## 💡 Architecture Decisions & Rationale

Here is the engineering rationale behind technology choices and design decisions:

### Why Medallion Architecture?
Data quality degrades as raw JSON API payloads contain anomalies. The medallion pattern organizes data into staging (Bronze), normalized intermediate (Silver), and serving (Gold) layers. This ensures downstream consumers (Streamlit) only query verified tables with conformed dimensions.

### Why PostgreSQL?
For a local-first reference platform, PostgreSQL 15 balances simplicity and capacity. Using JSONB fields enables native raw document storage, meaning we do not lose attributes when upstream APIs change. PostgreSQL regex pattern matching permits dbt-level mention scanning.

### Why dbt?
We treat transformations as modular SQL queries. dbt Core decouples compilation from execution, manages dependencies dynamically via the `ref()` function, enforces referential integrity through surrogate keys, and provides test compilation for data quality.

### Why Airflow?
We run ingestion tasks sequentially: `extract_github_events >> extract_hn_stories >> dbt_build >> dbt_test`. Apache Airflow handles retries with exponential backoff, provides isolated execution logging, and prevents bad data from reaching the warehouse via skipping dependencies on upstream errors.

### Why Separate Pipelines?
Ingesting GitHub events is unpaginated and immutable, while Hacker News story scores and comment counts change dynamically over time. Decoupling the clients enables independent rate limiting, customized retry configurations, and distinct database load profiles (GitHub uses `ON CONFLICT DO NOTHING` whereas HN uses `ON CONFLICT DO UPDATE`).

### Why Hacker News?
Hacker News represents the developer community's pulse. Combining repo-specific GitHub developer velocity with Hacker News mentions provides unified business intelligence: community buzz vs. actual engineering output.

### Future Connectors
The client factories and dbt sources are modularly defined. Adding third-party signals (e.g., Reddit developer subreddits, Dev.to articles, or Stack Overflow questions) follows the same pattern: write a raw database initialization script, create an ingestion client, add a dbt staging model, build Silver/Gold mentions, and expose the metrics in Streamlit.

---

## 🥈 Medallion Architecture Models

| Tier | Model | Type | Purpose |
|---|---|---|---|
| **Bronze** | `stg_github_events` | View | Staging for raw GitHub events; converts types. |
| **Bronze** | `stg_hn_stories` | View | Staging for raw HN stories; casts Unix timestamps. |
| **Silver** | `int_push_events` | View | Parses commit counts from raw PushEvent payloads. |
| **Silver** | `int_pull_requests` | View | Parses pull request actions (opened, closed, merged). |
| **Silver** | `int_hn_stories` | View | Filters items to valid stories; extracts URL domains. |
| **Silver** | `int_hn_repo_mentions` | View | Detects repo mentions in HN titles using postgres regex. |
| **Gold** | `dim_repository` | Table | Repository dimensional master; aggregates totals. |
| **Gold** | `dim_contributor` | Table | Unified developer dimension with type classification. |
| **Gold** | `dim_hn_story` | Table | Hacker News story dimension. |
| **Gold** | `fct_github_daily_activity` | Table | Daily fact rollup of GitHub commits and events. |
| **Gold** | `fct_contributor_daily_activity` | Table | Daily contribution facts per developer and repo. |
| **Gold** | `fct_hn_daily_activity` | Table | Daily fact rollup of HN story volume and upvotes. |
| **Gold** | `fct_hn_repo_mentions` | Table | Cross-source fact tracking daily repo mentions on HN. |

---

## 🧪 Data Quality Gates

We run **128 automated assertions** on every dbt build to ensure platform safety:
1.  **Uniqueness & Nullability**: Applied to all dimension surrogate keys and fact tables.
2.  **Referential Integrity**: Checks that fact tables link to valid conformed dimensions.
3.  **Accepted Values**: Restricts columns like `mentioned_repo`, `contrib_type`, and `story_type` to valid options.
4.  **Custom Business Rules**: SQL assertions to verify that commit counts are never negative, and event timestamps do not point to the future.

---

## 🚀 Getting Started

### Configuration (`.env`)

Clone the repo, copy `.env.example` to `.env`, and add your values:

```bash
# GitHub Config
GITHUB_TOKEN=ghp_yourpersonalaccesstokenhere

# Database Config
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=pipeone_warehouse
POSTGRES_USER=pipeone_user
POSTGRES_PASSWORD=your_secure_password_here

# Hacker News Config (Public API, no tokens needed)
HN_BASE_URL=https://hacker-news.firebaseio.com/v0
HN_TOP_STORY_LIMIT=50
HN_REQUEST_TIMEOUT=10
HN_USER_AGENT=PipeOne-HackerNews-Analytics
HN_MAX_RETRIES=3
HN_RETRY_BACKOFF=1.0
```

### Command-line Quickstart

1.  **Start Infrastructure**:
    ```bash
    docker-compose up -d
    ```
2.  **Initialize Warehouses**:
    ```bash
    python src/database/init_db.py
    python src/database/init_hn_db.py
    ```
3.  **Run Ingestion Clients**:
    ```bash
    python src/ingestion/github_client.py
    python src/ingestion/hn_client.py
    ```
4.  **Execute dbt Transformations & Tests**:
    ```bash
    cd dbt_project
    dbt build --target dev
    ```
5.  **Launch Analytics Console**:
    ```bash
    streamlit run src/dashboard/app.py
    ```

---

## 👤 Author & Maintainer

**Diwakar Kaushik**  
CSE — Data Engineering & AI · Lovely Professional University  
📧 devkaushik6906@gmail.com · 🐙 [@Diw696](https://github.com/Diw696)