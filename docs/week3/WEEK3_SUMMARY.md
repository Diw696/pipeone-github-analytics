# Week 3 Summary — Gold Layer Implementation

## Objective

The objective of Week 3 was to transform the cleaned Silver layer into an analytics-ready Gold layer using dimensional modeling.

The Gold layer prepares the data for dashboards and reporting by organizing it into fact and dimension tables. Instead of calculating metrics every time a dashboard loads, these calculations are performed once inside the data warehouse, making reporting simpler, faster, and more consistent.

---

# Current Project Architecture

```
                        GitHub Events API
                               │
                               ▼
                    Python Ingestion Client
                 (Extract + Load, Idempotent)
                               │
                               ▼
                  PostgreSQL Warehouse (JSONB)
                 github_events_raw (Raw Table)
                               │
                               ▼
                Bronze Layer (dbt Staging Model)
                  stg_github_events
                               │
                               ▼
              Silver Layer (Business Models)
        ┌──────────────────────────────────────┐
        │                                      │
        ▼                                      ▼
 int_push_events                     int_pull_requests
        │                                      │
        └──────────────────┬───────────────────┘
                           ▼
                 Gold Layer (Analytics)
        ┌──────────────────────────────────────┐
        │                                      │
        ▼                                      ▼
  dim_repository                     dim_contributor
        │                                      │
        └───────────────┬──────────────────────┘
                        ▼
      fct_github_daily_activity
                        │
                        ▼
  fct_contributor_daily_activity
                        │
                        ▼
          Dashboard & Business Analytics
```

---

# Medallion Architecture

Our project now follows the Medallion Architecture.

## Bronze Layer

Purpose:

Store standardized raw events.

Responsibilities:

- Read from PostgreSQL raw table
- Standardize column types
- Preserve raw JSON payload
- No business logic

Model:

- `stg_github_events`

---

## Silver Layer

Purpose:

Transform raw GitHub events into clean business models.

Responsibilities:

- Parse JSONB
- Separate Push Events
- Separate Pull Request Events
- Flatten nested structures
- Create analytics-ready columns

Models:

- `int_push_events`
- `int_pull_requests`

---

## Gold Layer

Purpose:

Prepare data specifically for reporting and dashboards.

Responsibilities:

- Aggregate business metrics
- Create dimension tables
- Create fact tables
- Reduce dashboard complexity
- Improve reporting performance

Models:

- `dim_repository`
- `dim_contributor`
- `fct_github_daily_activity`
- `fct_contributor_daily_activity`

---

# Gold Layer Models

## 1. dim_repository

Type:

Dimension Table

Grain:

One row per repository.

Purpose:

Stores descriptive information about each monitored repository.

Contains:

- Repository ID
- Repository Name
- Owner
- Language
- Stars
- Total Push Events
- Total Pull Request Events
- First Activity Date
- Last Activity Date

Business Value:

Provides a single source of repository information for reporting.

---

## 2. dim_contributor

Type:

Dimension Table

Grain:

One row per contributor.

Purpose:

Stores contributor information collected from both Push Events and Pull Request Events.

Contains:

- Contributor ID
- Username
- Contributor Type
- Total Push Events
- Total Pull Requests
- Total Commits
- First Activity
- Last Activity

Business Value:

Allows dashboards to analyze contributor activity without repeatedly processing raw event data.

---

## 3. fct_github_daily_activity

Type:

Fact Table

Grain:

One row per Repository per Day.

Purpose:

Stores daily repository metrics.

Contains metrics such as:

- Push Count
- Commit Count
- Pull Requests Opened
- Pull Requests Closed
- Pull Requests Merged
- Total Activity

Business Value:

Supports repository-level dashboards and trend analysis.

---

## 4. fct_contributor_daily_activity

Type:

Fact Table

Grain:

One row per Contributor, Repository, and Day.

Purpose:

Stores daily contributor activity.

Contains:

- Contributor
- Repository
- Activity Date
- Push Count
- Commit Count
- Pull Request Metrics
- Total Activity

Business Value:

Supports contributor leaderboards and detailed activity analysis.

---

# Key Concepts Learned

During Week 3, the following concepts were implemented and understood:

- Fact Tables
- Dimension Tables
- Star Schema
- Table Grain
- Business Keys
- Surrogate Keys (MD5)
- Relationship Testing
- Data Aggregation
- Warehouse Modeling
- Analytics-Oriented Data Design

---

# Why We Built a Gold Layer

The Silver layer contains clean event data, but dashboards still require calculations such as:

- Daily commits
- Daily pull requests
- Contributor activity
- Repository statistics

If every dashboard calculated these metrics independently:

- Queries become slower
- Business logic becomes duplicated
- Different dashboards may show different numbers

The Gold layer solves this by calculating metrics once inside the warehouse.

As a result:

- Dashboards become simpler.
- Queries become faster.
- Business metrics stay consistent.

---

# Data Quality

The Gold layer extends the existing dbt testing framework.

Tests include:

- Unique Keys
- Not Null Constraints
- Accepted Values
- Relationship Tests
- Referential Integrity

These automated tests ensure that every fact table references valid dimension records and that important business fields remain consistent.

---

# Project Progress

## Week 1

Completed:

- Docker Compose
- PostgreSQL
- GitHub API Ingestion
- JSONB Storage
- Idempotent Loading

---

## Week 2

Completed:

- dbt Setup
- Bronze Layer
- Silver Layer
- Automated Testing
- Data Quality Framework

---

## Week 3

Completed:

- Gold Layer
- Star Schema
- Fact Tables
- Dimension Tables
- Warehouse Modeling
- Dashboard-ready Data

---

# Current Pipeline Status

```
Infrastructure        ✅ Complete
Python Ingestion      ✅ Complete
PostgreSQL Warehouse  ✅ Complete
Bronze Layer          ✅ Complete
Silver Layer          ✅ Complete
Gold Layer            ✅ Complete
Data Quality Tests    ✅ Passing
Dashboard             ⏳ Next Phase
```

---

# What We Learned

Week 3 shifted the project from data transformation to business analytics.

Instead of simply cleaning GitHub events, we learned how analytics platforms organize data for reporting using dimensional modeling.

The biggest takeaway was understanding that dashboards should consume pre-computed business models rather than raw transactional data. By separating the warehouse into Bronze, Silver, and Gold layers, the pipeline became easier to understand, easier to test, and easier to extend in the future.

---

# Next Step

The next phase of the project is Dashboard Development.

The dashboard will connect directly to the Gold layer and visualize:

- Repository Activity
- Daily Commit Trends
- Pull Request Metrics
- Contributor Leaderboards
- Overall Project Health

No additional transformation logic should be required inside the dashboard because all business calculations already exist in the Gold layer.

---

# Week 3 Outcome

By the end of Week 3, PipeOne had evolved into a complete analytics warehouse.

The project now follows a modern ELT architecture:

GitHub API → Python → PostgreSQL → Bronze → Silver → Gold

The pipeline produces clean, validated, analytics-ready datasets that are prepared for visualization in the final phase of the project.