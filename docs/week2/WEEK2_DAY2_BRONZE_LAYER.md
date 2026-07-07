# Week 2 - Day 1 Progress Report
## Infrastructure Setup & Bronze Layer Initialization

**Date:** July 7, 2026

---

# Objective

The objective of today's work was to prepare the Analytics Engineering environment for PipeOne and build the first dbt Bronze Layer.

Instead of writing transformation logic directly on the raw PostgreSQL table, we introduced dbt as the transformation framework that will manage all downstream data models.

---

# Work Completed

## 1. dbt Environment Setup

- Installed `dbt-core`
- Installed `dbt-postgres`
- Initialized a new dbt project
- Configured `profiles.yml` outside the repository
- Successfully connected dbt to the PostgreSQL warehouse
- Verified configuration using `dbt debug`

---

## 2. Bronze Layer

### Source Registration

Created:

```
models/staging/_sources.yml
```

Registered the existing raw table:

```
public.github_events_raw
```

This allows dbt to:
- Track source lineage
- Generate documentation
- Apply source-level tests
- Reference tables using the `source()` macro

---

### Staging Model

Created:

```
models/staging/stg_github_events.sql
```

The staging model:

- Reads data from the raw GitHub events table
- Casts `fetched_at` to a proper timestamp
- Preserves the `raw_payload` JSONB column
- Applies no business logic

This model serves as the Bronze Layer entry point for all future transformations.

---

# Commands Executed

```bash
dbt debug
dbt ls
dbt parse
dbt run
```

All commands completed successfully.

---

# Result

dbt successfully created the first staging model:

```
public.stg_github_events
```

The model is materialized as a **VIEW**, meaning it always reflects the latest data from the raw ingestion table without duplicating storage.

---

# Current Architecture

```
GitHub API
      │
      ▼
Python Ingestion
      │
      ▼
github_events_raw
(Raw Landing Table)
      │
      ▼
stg_github_events
(Bronze Layer)
```

---

# Key Learnings

- Understood the difference between Data Engineering (Python ingestion) and Analytics Engineering (dbt transformations).
- Learned how dbt Sources register existing warehouse tables.
- Built the first Bronze Layer staging model following Medallion Architecture.
- Learned the purpose of `dbt debug`, `dbt parse`, `dbt ls`, and `dbt run`.
- Understood why staging models remain lightweight and avoid business logic.

---

# Status

✅ dbt environment configured

✅ PostgreSQL connection verified

✅ Bronze Layer operational

✅ First dbt model created successfully

---

# Next Steps

- Build Silver Layer transformation models.
- Extract structured fields from the `raw_payload` JSONB column.
- Create event-specific models for Push Events and Pull Request Events.
- Add dbt schema tests and data quality validations.