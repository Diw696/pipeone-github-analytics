# Week 2 Architecture: Adding dbt to the Pipeline

This document explains how dbt fits into the PipeOne data pipeline and what problem it solves.

---

## The Problem (Week 1 State)

After Week 1, we had raw GitHub events stored as JSONB in PostgreSQL:

```sql
SELECT * FROM github_events_raw LIMIT 1;
```

**Result:**
```
event_id  | repo_name      | event_type | fetched_at           | raw_payload
----------|----------------|------------|----------------------|------------------
12345678  | facebook/react | PushEvent  | 2026-07-03 10:30:00  | {"id": "12345678", ...
```

**Problem:** The `raw_payload` column contains ALL event data as unstructured JSON:

```json
{
  "id": "12345678",
  "type": "PushEvent",
  "actor": {
    "id": 123,
    "login": "alice",
    "display_login": "alice",
    "gravatar_id": "",
    "url": "https://api.github.com/users/alice",
    "avatar_url": "https://avatars.githubusercontent.com/u/123?"
  },
  "repo": {
    "id": 10270250,
    "name": "facebook/react",
    "url": "https://api.github.com/repos/facebook/react"
  },
  "payload": {
    "push_id": 9876543210,
    "size": 3,
    "distinct_size": 3,
    "ref": "refs/heads/main",
    "head": "a1b2c3d4e5f6...",
    "before": "f6e5d4c3b2a1...",
    "commits": [
      {
        "sha": "a1b2c3d4...",
        "author": {
          "email": "alice@example.com",
          "name": "Alice Developer"
        },
        "message": "Fix typo in documentation",
        "distinct": true,
        "url": "https://api.github.com/repos/facebook/react/commits/a1b2c3d4..."
      }
    ]
  },
  "public": true,
  "created_at": "2026-07-03T10:25:30Z"
}
```

**Challenges:**

1. **Hard to query** - Need to use JSON operators: `raw_payload->>'type'`, `raw_payload->'actor'->>'login'`
2. **No type safety** - Everything is text, PostgreSQL can't enforce data types
3. **Slow performance** - Parsing JSON on every query is expensive
4. **Not analytics-ready** - Dashboards need flat, typed tables, not nested JSON
5. **Duplicate logic** - Every analyst writes the same JSON parsing code

---

## The Solution: dbt Transformations

dbt sits **between** raw storage and analytics consumption:

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Pipeline Flow                       │
└─────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  GitHub Events   │  External API (read-only)
│  API             │  Returns: JSON events
└────────┬─────────┘
         │ HTTP GET requests
         ▼
┌──────────────────┐
│  Python Client   │  Week 1: Extract & Load
│  (github_client  │  - Fetch raw JSON
│  .py)            │  - Insert into PostgreSQL
└────────┬─────────┘
         │ INSERT statements
         ▼
┌──────────────────────────────────────────────────────────────┐
│                  PostgreSQL Database                         │
│                  (pipeone_warehouse)                         │
├──────────────────────────────────────────────────────────────┤
│  PUBLIC SCHEMA (Bronze Layer - Raw Data)                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  github_events_raw                                 │    │
│  │  - event_id (VARCHAR)                              │    │
│  │  - repo_name (VARCHAR)                             │    │
│  │  - event_type (VARCHAR)                            │    │
│  │  - fetched_at (TIMESTAMP)                          │    │
│  │  - raw_payload (JSONB) ← Nested, unstructured     │    │
│  └────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           │ dbt reads from here              │
│                           ▼                                  │
│                      ┌─────────┐                             │
│                      │   dbt   │  Week 2: Transform          │
│                      │ (models)│  - Parse JSON               │
│                      └────┬────┘  - Type conversion          │
│                           │       - Business logic           │
│                           │ dbt writes to here               │
│                           ▼                                  │
│  DBT_DEV SCHEMA (Silver Layer - Typed Data)                 │
│  ┌────────────────────────────────────────────────────┐    │
│  │  stg_push_events (view)                            │    │
│  │  - event_id (VARCHAR)                              │    │
│  │  - repo_name (VARCHAR)                             │    │
│  │  - actor_login (VARCHAR) ← Extracted from JSON    │    │
│  │  - commit_count (INTEGER) ← Typed!                │    │
│  │  - commit_message (TEXT)                           │    │
│  │  - created_at (TIMESTAMP)                          │    │
│  └────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  stg_pull_requests (view)                          │    │
│  │  - event_id (VARCHAR)                              │    │
│  │  - repo_name (VARCHAR)                             │    │
│  │  - pr_number (INTEGER)                             │    │
│  │  - pr_action (VARCHAR)                             │    │
│  │  - actor_login (VARCHAR)                           │    │
│  └────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           │ dbt aggregates                   │
│                           ▼                                  │
│  DBT_DEV SCHEMA (Gold Layer - Analytics)                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  daily_repo_activity (table)                       │    │
│  │  - date (DATE)                                     │    │
│  │  - repo_name (VARCHAR)                             │    │
│  │  - total_events (INTEGER)                          │    │
│  │  - push_count (INTEGER)                            │    │
│  │  - pr_count (INTEGER)                              │    │
│  │  - unique_contributors (INTEGER)                   │    │
│  └────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
         │ SELECT queries
         ▼
┌──────────────────┐
│  Streamlit       │  Week 4: Visualization
│  Dashboard       │  - Charts from Gold layer
└──────────────────┘  - No JSON parsing needed
```

---

## What dbt Does (Step by Step)

### Step 1: Read Raw Data

dbt reads from `public.github_events_raw`:

```sql
-- Inside dbt model: models/staging/stg_push_events.sql
SELECT
    event_id,
    repo_name,
    raw_payload
FROM {{ source('public', 'github_events_raw') }}
WHERE event_type = 'PushEvent'
```

### Step 2: Parse JSON (Silver Layer)

Extract fields from the nested JSONB:

```sql
-- models/staging/stg_push_events.sql
SELECT
    event_id,
    repo_name,
    raw_payload->>'type' AS event_type,
    raw_payload->'actor'->>'login' AS actor_login,
    (raw_payload->'payload'->>'size')::INTEGER AS commit_count,
    raw_payload->'payload'->'commits'->0->>'message' AS commit_message,
    (raw_payload->>'created_at')::TIMESTAMP AS created_at
FROM {{ source('public', 'github_events_raw') }}
WHERE raw_payload->>'type' = 'PushEvent'
```

**Result:** dbt creates a **view** called `dbt_dev.stg_push_events`:

```
event_id  | repo_name      | actor_login | commit_count | commit_message         | created_at
----------|----------------|-------------|--------------|------------------------|---------------------
12345678  | facebook/react | alice       | 3            | Fix typo in docs       | 2026-07-03 10:25:30
12345679  | microsoft/vsc… | bob         | 1            | Update dependencies    | 2026-07-03 10:30:15
```

✅ **Benefits:**
- Flat table (no nested JSON)
- Typed columns (INTEGER, TIMESTAMP)
- Fast queries (no JSON parsing at query time)

### Step 3: Aggregate (Gold Layer)

Build business metrics:

```sql
-- models/marts/daily_repo_activity.sql
SELECT
    DATE(created_at) AS date,
    repo_name,
    COUNT(*) AS total_push_events,
    SUM(commit_count) AS total_commits,
    COUNT(DISTINCT actor_login) AS unique_contributors
FROM {{ ref('stg_push_events') }}
GROUP BY 1, 2
```

**Result:** dbt creates a **table** called `dbt_dev.daily_repo_activity`:

```
date       | repo_name      | total_push_events | total_commits | unique_contributors
-----------|----------------|-------------------|---------------|--------------------
2026-07-03 | facebook/react | 45                | 120           | 23
2026-07-03 | microsoft/vsc… | 38                | 85            | 19
```

✅ **Benefits:**
- Pre-aggregated (fast dashboard queries)
- Business-friendly column names
- No complex SQL needed by dashboard

---

## Three-Layer Architecture (Bronze/Silver/Gold)

### Bronze Layer (`public` schema)

**Purpose:** Store raw data exactly as received

**Characteristics:**
- No transformations
- Keep everything (even errors)
- Source of truth
- Append-only

**Tables:**
- `public.github_events_raw` (Week 1 ingestion writes here)

**Example query:**
```sql
-- Count total raw events
SELECT COUNT(*) FROM public.github_events_raw;
```

### Silver Layer (`dbt_dev` schema)

**Purpose:** Clean, type, and structure data

**Characteristics:**
- Parse nested fields
- Type conversions (string → integer, string → timestamp)
- Remove duplicates
- Filter invalid records
- One model per event type

**Tables/Views:**
- `dbt_dev.stg_push_events` (parsed push events)
- `dbt_dev.stg_pull_requests` (parsed PR events)
- `dbt_dev.stg_issues` (parsed issue events)

**Example query:**
```sql
-- Count push events by repository
SELECT repo_name, COUNT(*)
FROM dbt_dev.stg_push_events
GROUP BY repo_name;
```

### Gold Layer (`dbt_dev` schema)

**Purpose:** Business metrics and aggregations

**Characteristics:**
- Pre-calculated metrics
- Joined data from multiple sources
- Time-series aggregations
- Dashboard-ready tables

**Tables:**
- `dbt_dev.daily_repo_activity` (daily metrics by repo)
- `dbt_dev.contributor_stats` (contributor leaderboards)
- `dbt_dev.event_trends` (weekly/monthly trends)

**Example query:**
```sql
-- Get last 7 days of activity
SELECT *
FROM dbt_dev.daily_repo_activity
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY date DESC, total_commits DESC;
```

---

## Why Separate Schemas?

### Option 1: Everything in `public` (BAD)

```
pipeone_warehouse/public/
├── github_events_raw
├── stg_push_events
├── stg_pull_requests
└── daily_repo_activity
```

**Problems:**
- Hard to tell raw vs. transformed data
- Can't easily drop/rebuild transformations
- Confusion about which tables to query

### Option 2: Separate schemas (GOOD)

```
pipeone_warehouse/
├── public/
│   └── github_events_raw (raw data - never touched by dbt)
└── dbt_dev/
    ├── stg_push_events (dbt creates this)
    ├── stg_pull_requests (dbt creates this)
    └── daily_repo_activity (dbt creates this)
```

**Benefits:**
- Clear ownership: `public` = ingestion, `dbt_dev` = dbt
- Safe rebuilds: `DROP SCHEMA dbt_dev CASCADE` doesn't touch raw data
- Environment separation: `dbt_dev` (local), `dbt_prod` (production)

---

## dbt Workflow

### 1. Write SQL Model

Create `models/staging/stg_push_events.sql`:

```sql
SELECT
    event_id,
    repo_name,
    raw_payload->'actor'->>'login' AS actor_login,
    (raw_payload->'payload'->>'size')::INTEGER AS commit_count
FROM {{ source('public', 'github_events_raw') }}
WHERE raw_payload->>'type' = 'PushEvent'
```

### 2. Run dbt

```bash
cd dbt_project
dbt run --models stg_push_events
```

**What happens:**
1. dbt reads your SQL file
2. Compiles it (replaces `{{ source(...) }}` with actual table name)
3. Executes: `CREATE VIEW dbt_dev.stg_push_events AS ...`
4. Logs result (success/failure)

### 3. Query the Result

```sql
SELECT * FROM dbt_dev.stg_push_events LIMIT 10;
```

You now have a clean, typed view of push events!

### 4. Iterate

- Update the SQL file
- Run `dbt run` again
- dbt drops and recreates the view

---

## dbt vs. Manual SQL Scripts

### Manual Approach (Week 1 style)

```sql
-- push_events.sql
DROP VIEW IF EXISTS dbt_dev.stg_push_events;

CREATE VIEW dbt_dev.stg_push_events AS
SELECT
    event_id,
    repo_name,
    raw_payload->'actor'->>'login' AS actor_login
FROM public.github_events_raw
WHERE raw_payload->>'type' = 'PushEvent';
```

**Problems:**
1. **No dependency management** - If you have 10 scripts, what order do you run them?
2. **No testing** - How do you ensure `actor_login` is never NULL?
3. **No documentation** - Where do you explain what each column means?
4. **No version control** - How do you track changes over time?
5. **Manual execution** - Have to remember to run every script

### dbt Approach

```sql
-- models/staging/stg_push_events.sql
{{ config(materialized='view') }}

SELECT
    event_id,
    repo_name,
    raw_payload->'actor'->>'login' AS actor_login
FROM {{ source('public', 'github_events_raw') }}
WHERE raw_payload->>'type' = 'PushEvent'
```

**Benefits:**
1. **Automatic dependencies** - dbt figures out the correct execution order
2. **Built-in testing** - Add `tests:` in schema.yml to check for nulls
3. **Auto-generated docs** - Run `dbt docs generate` for documentation site
4. **Git integration** - All models in version control
5. **One command** - `dbt run` executes everything in the right order

---

## Key Terminology

### Model
A SQL file in the `models/` directory. Each model creates one table or view.

**Example:** `models/staging/stg_push_events.sql` → `dbt_dev.stg_push_events`

### Source
A reference to a raw table (usually created outside dbt).

**Example:** `{{ source('public', 'github_events_raw') }}`

### Ref
A reference to another dbt model (creates dependencies).

**Example:** `{{ ref('stg_push_events') }}` → waits for `stg_push_events` to build first

### Materialization
How dbt creates the database object.

**Options:**
- `view` - Fast to build, slow to query (re-parses JSON every time)
- `table` - Slow to build, fast to query (pre-computed)
- `incremental` - Only processes new records (advanced)
- `ephemeral` - CTE only, not materialized

### Target
Which environment to build in (dev, prod, staging).

**Example:** `dbt run --target prod` → builds in `dbt_prod` schema

---

## Week 2 Roadmap

### Day 1 (Today) ✅
- Install dbt-postgres
- Create project structure
- Configure profiles.yml
- Test connection

### Day 2 (Next)
- Create first staging model (`stg_push_events`)
- Learn `{{ source() }}` and `{{ ref() }}`
- Understand view vs. table materialization
- Run `dbt run` and query results

### Day 3
- Add more staging models (`stg_pull_requests`, `stg_issues`)
- Write dbt tests (not_null, unique, relationships)
- Create schema.yml documentation

### Day 4-5
- Build Gold layer aggregations
- Create `daily_repo_activity` mart
- Test end-to-end pipeline
- Prepare for Week 3 (scheduling)

---

## Common Questions

### Q: Why not just use SQL views directly?

**A:** You could, but dbt provides:
- Automatic dependency management (run models in correct order)
- Built-in testing framework (data quality checks)
- Documentation generation (auto-generated docs site)
- Environment management (dev vs. prod)
- Incremental builds (only process new data)

dbt is like using Git instead of just saving files - yes, you *could* do it manually, but the tooling makes life much easier.

### Q: Does dbt replace PostgreSQL?

**A:** No. dbt **requires** a database to work. Think of it as:
- PostgreSQL = the warehouse (stores data)
- dbt = the forklift (organizes data inside the warehouse)

You can't use dbt without an underlying database.

### Q: Can I delete the Bronze layer after creating Silver layer?

**A:** No! The Bronze layer (`public.github_events_raw`) is your source of truth. If you realize you need a new field from the JSON, you can only get it from the Bronze layer.

**Rule:** Never delete raw data. Disk space is cheap, re-ingesting data is expensive.

### Q: What happens if I run `dbt run` twice?

**A:** For views, dbt drops and recreates them (idempotent - same result). For tables, it depends on materialization strategy (full refresh vs. incremental).

Safe to run multiple times - dbt is designed for this!

---

## Next Steps

1. ✅ Complete profiles.yml setup
2. ✅ Run `dbt debug` (verify connection)
3. Read this architecture doc
4. Move to Day 2: Create first staging model

**Once you understand this architecture, you're ready to build your first transformation!**
