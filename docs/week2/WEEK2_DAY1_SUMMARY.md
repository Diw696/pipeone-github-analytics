# Week 2 - Day 1 Complete: dbt Infrastructure Setup

**Date:** July 6, 2026  
**Status:** ✅ Complete  
**Scope:** Infrastructure ONLY - No models, transformations, or tests yet

---

## What We Built Today

Today was all about **setting up the toolbox** for data transformations. We installed dbt, configured the project structure, and established a connection to PostgreSQL.

Think of it like this:
- **Week 1:** Built the data pipeline (Extract → Load)
- **Week 2 Day 1:** Installed transformation tools (dbt infrastructure)
- **Week 2 Day 2+:** Build actual transformations (coming next)

---

## Files Created

### 1. dbt Project Configuration
- **`dbt_project/dbt_project.yml`** - Main dbt project configuration
  - Project name: `pipeone_dbt`
  - Profile reference: `pipeone`
  - Directory paths for models, tests, seeds, etc.

### 2. Database Connection Template
- **`dbt_project/profiles.yml.example`** - Database connection template
  - PostgreSQL connection settings
  - Dev and prod environments configured
  - **Must be copied to `~/.dbt/profiles.yml` and password updated**

### 3. Setup Automation
- **`dbt_project/setup_dbt_profile.ps1`** - PowerShell script to automate profiles.yml installation
  - Creates `~/.dbt/` directory if needed
  - Copies profiles.yml.example to correct location
  - Prompts for overwrite if file exists

### 4. Documentation
- **`dbt_project/README_SETUP.md`** - Comprehensive setup guide with:
  - Step-by-step installation instructions
  - Explanation of every field in profiles.yml and dbt_project.yml
  - Troubleshooting section for common errors
  - Interview questions to test understanding
  - Architecture diagrams and folder structure

### 5. Project Structure
Created standard dbt directories (all empty for now):
- **`models/`** - Future: SQL transformation models
- **`tests/`** - Future: Data quality tests
- **`analyses/`** - Future: Ad-hoc analysis queries
- **`seeds/`** - Future: CSV reference data
- **`macros/`** - Future: Reusable SQL functions
- **`snapshots/`** - Future: Slowly changing dimensions

### 6. Git Configuration
- **`dbt_project/.gitignore`** - Protects dbt artifacts and credentials
  - Ignores: target/, dbt_packages/, logs/, profiles.yml

---

## Updated Files

### `requirements.txt`
Added dbt and its dependencies:
```
# dbt Dependencies - Week 2
dbt-postgres==1.7.4
```

This installs:
- `dbt-core==1.7.4` - Core dbt functionality
- `dbt-postgres==1.7.4` - PostgreSQL adapter
- Plus 20+ dependencies (Jinja2, SQLAlchemy, etc.)

---

## Next Steps for You

### Step 1: Set Up profiles.yml

**Option A: Use the helper script (recommended)**
```powershell
cd dbt_project
.\setup_dbt_profile.ps1
```

**Option B: Manual setup**
```powershell
# Create directory
mkdir $env:USERPROFILE\.dbt

# Copy file
copy dbt_project\profiles.yml.example $env:USERPROFILE\.dbt\profiles.yml
```

### Step 2: Update Password

1. Open `C:\Users\asus\.dbt\profiles.yml`
2. Find: `password: your_secure_password_here`
3. Replace with your actual PostgreSQL password (from `.env` file)
4. Save the file

### Step 3: Test Connection

```bash
cd dbt_project
dbt debug
```

**Expected output:**
```
12:09:00  All checks passed!
```

If you see errors, check the **Troubleshooting** section in `README_SETUP.md`.

---

## Architecture Overview

### Where dbt Fits in the Pipeline

```
┌──────────────────────┐
│   GitHub Events API  │  Week 1: Data Source
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Python Ingestion    │  Week 1: Extract & Load
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  PostgreSQL          │  Week 1: Raw Data Storage
│  public.github_      │  - Raw JSONB events
│  events_raw          │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  dbt                 │  Week 2: Transform (TODAY'S SETUP)
│  Transformations     │  - Parse JSONB
│                      │  - Create typed tables
│                      │  - Aggregate metrics
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  PostgreSQL          │  Week 2: Transformed Data
│  dbt_dev.stg_*       │  - Staging models
│  dbt_dev.fact_*      │  - Analytics models
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Streamlit Dashboard │  Week 4: Visualization
└──────────────────────┘
```

### Current State vs. Future State

**What we have NOW (after Week 2 Day 1):**
```
pipeone_warehouse (database)
└── public (schema)
    └── github_events_raw (table)
        ├── event_id (VARCHAR)
        ├── repo_name (VARCHAR)
        ├── event_type (VARCHAR)
        ├── fetched_at (TIMESTAMP)
        └── raw_payload (JSONB) ← All the nested JSON data
```

**What we'll have AFTER Week 2 (with dbt models):**
```
pipeone_warehouse (database)
├── public (schema)
│   └── github_events_raw (table) ← Original raw data (unchanged)
│
└── dbt_dev (schema)
    ├── stg_push_events (view)
    │   ├── event_id
    │   ├── repo_name
    │   ├── actor_login
    │   ├── commit_count
    │   └── created_at
    │
    ├── stg_pull_requests (view)
    │   ├── event_id
    │   ├── repo_name
    │   ├── pr_number
    │   ├── pr_action
    │   └── created_at
    │
    └── daily_repo_activity (table)
        ├── date
        ├── repo_name
        ├── total_events
        ├── push_count
        └── pr_count
```

**Key insight:** Raw data stays in `public` schema. dbt creates new tables/views in `dbt_dev` schema. This separation makes it easy to rebuild transformations without touching raw data.

---

## Technical Decisions Made

### Decision 1: dbt-core vs. dbt-cloud

**Choice:** dbt-core (open-source, runs locally)

**Why:**
- Free and open-source
- Full control over execution
- Works offline
- Good for learning fundamentals

**Tradeoff:** dbt Cloud has a nicer web UI and built-in scheduling, but dbt-core is sufficient for Week 2 learning goals.

### Decision 2: profiles.yml location

**Choice:** `~/.dbt/profiles.yml` (outside project directory)

**Why:**
- Security: Never accidentally committed to Git
- Shared across multiple dbt projects
- Standard dbt convention

**What breaks if removed:** dbt can't find database credentials, all dbt commands fail.

### Decision 3: Schema naming

**Choice:** `dbt_dev` (separate from `public`)

**Why:**
- Clear separation: raw data (public) vs. transformed data (dbt_dev)
- Easy to drop and rebuild dbt_dev without touching raw data
- Matches industry best practices (Bronze/Silver/Gold layers)

**Alternative:** Could have used `public` for everything, but harder to organize and troubleshoot.

### Decision 4: threads: 4

**Choice:** 4 parallel threads

**Why:**
- Modern laptops have 4+ CPU cores
- Faster model builds (4x speedup for independent models)
- Not too high to overwhelm PostgreSQL

**What breaks if set too high:** PostgreSQL connection pool exhaustion, slower performance due to context switching.

---

## Key Concepts to Understand

### 1. dbt is NOT a database

**Common confusion:** "Is dbt a database like PostgreSQL?"

**Answer:** No. dbt is a **transformation tool** that runs SQL queries against an existing database.

Think of it like this:
- PostgreSQL = the warehouse building (stores data)
- dbt = the forklift (moves and organizes data inside the warehouse)

You can't use dbt without an underlying database.

### 2. Models vs. Tables

**dbt model** = A SQL file that defines a transformation

**Database table/view** = What dbt creates when you run that model

Example:
- `models/staging/stg_push_events.sql` = dbt model (SQL file)
- `dbt_dev.stg_push_events` = database view (created by dbt)

One SQL file → One database object.

### 3. Profiles vs. Projects

**profiles.yml** = WHERE to run (database connection)  
**dbt_project.yml** = WHAT to run (project configuration)

You can have:
- 1 profile (connection) → many projects
- 1 project → many profiles (dev, prod, staging)

This is why profiles.yml lives in `~/.dbt/` (shared across projects) while dbt_project.yml lives in each project folder.

### 4. Schemas as Data Layers

Using separate schemas is a common data warehouse pattern:

**Bronze Layer** (`public` schema) - Raw data, exactly as ingested
- No transformations
- Keep everything
- source of truth

**Silver Layer** (`dbt_dev` schema) - Cleaned, typed data
- Parse JSON
- Remove duplicates
- Type conversions

**Gold Layer** (`dbt_dev` schema) - Business metrics
- Aggregations
- Joins
- Ready for dashboard

We're building Silver and Gold layers in Week 2.

---

## Interview Questions (Test Your Understanding)

### Question 1
**You run `dbt debug` and get "profile 'pipeone' does not exist". What's the problem?**

<details>
<summary>Answer</summary>

The `profiles.yml` file either:
1. Doesn't exist at `~/.dbt/profiles.yml`
2. Exists but doesn't have a `pipeone:` profile defined
3. Is in the wrong location (e.g., inside dbt_project/ instead of ~/.dbt/)

**Fix:** Run `.\setup_dbt_profile.ps1` to create the file in the correct location.
</details>

### Question 2
**What's the difference between `dbt_project.yml` and `profiles.yml`?**

<details>
<summary>Answer</summary>

- **dbt_project.yml** = Project configuration (WHAT to build)
  - Project name, paths, model configs
  - Lives inside project directory
  - Committed to Git

- **profiles.yml** = Database connection (WHERE to build)
  - Host, port, username, password
  - Lives in ~/.dbt/ (outside project)
  - **Never** committed to Git (contains secrets)

Think: dbt_project.yml = the recipe, profiles.yml = the kitchen location.
</details>

### Question 3
**Why does profiles.yml live in `~/.dbt/` instead of inside `dbt_project/`?**

<details>
<summary>Answer</summary>

**Primary reason:** Security. profiles.yml contains database passwords. By keeping it outside the project directory, we ensure it never gets accidentally committed to Git.

**Secondary reason:** Reusability. One profiles.yml can be shared across multiple dbt projects (e.g., if you have multiple data projects using the same warehouse).

Similar to how .env files are gitignored, but profiles.yml gets an extra layer of protection by living outside the repo entirely.
</details>

### Question 4
**You want dbt to create tables in the `analytics` schema instead of `dbt_dev`. Where do you change this?**

<details>
<summary>Answer</summary>

In `~/.dbt/profiles.yml`, change:

```yaml
schema: dbt_dev
```

to:

```yaml
schema: analytics
```

Then run `dbt debug` to verify the connection still works.

**Note:** This changes where dbt writes transformed data. It doesn't affect where raw data lives (public.github_events_raw).
</details>

### Question 5
**Explain this file structure in your own words:**

```
pipeone_warehouse/
├── public/
│   └── github_events_raw
└── dbt_dev/
    ├── stg_push_events
    └── daily_repo_activity
```

<details>
<summary>Answer</summary>

**Database:** `pipeone_warehouse` - The PostgreSQL database (the "warehouse building")

**Schema: `public`** - Default schema, contains raw ingested data
- `github_events_raw` - Week 1 ingestion writes raw JSON events here

**Schema: `dbt_dev`** - dbt development schema, contains transformed data
- `stg_push_events` - dbt model that parses push event fields from JSON
- `daily_repo_activity` - dbt model that aggregates events by date/repo

**Key insight:** Raw data (public) stays unchanged. dbt creates new objects (dbt_dev) based on raw data. If dbt transformations break, raw data is safe.
</details>

---

## What We Did NOT Do Today

❌ Create any SQL transformation models  
❌ Write any dbt tests  
❌ Parse JSONB fields  
❌ Build aggregation tables  
❌ Set up CI/CD for dbt  
❌ Configure dbt docs  

**These are all Week 2 Day 2+ tasks.**

Today was purely about installing tools and establishing database connectivity.

---

## Git Commit Message (Suggested)

```
feat(week2): Add dbt infrastructure setup (Day 1)

Infrastructure:
- Add dbt-postgres==1.7.4 to requirements.txt
- Create dbt_project/ directory structure (models, tests, seeds, etc.)
- Configure dbt_project.yml with project settings (name: pipeone_dbt, profile: pipeone)
- Add profiles.yml.example template for PostgreSQL connection
- Create setup_dbt_profile.ps1 automation script
- Add .gitignore for dbt artifacts and credentials

Documentation:
- Create comprehensive README_SETUP.md with step-by-step instructions
- Explain every profiles.yml field (host, port, schema, threads, etc.)
- Add troubleshooting guide for common dbt debug errors
- Include interview questions to test understanding
- Document architecture: where dbt fits in the data pipeline

Status: Week 2 Day 1 complete ✅
Scope: Infrastructure ONLY - no models, transformations, or tests yet
Next: Day 2 - Create first staging model (stg_push_events.sql)
```

---

## Summary

### Accomplished Today

✅ Installed dbt-postgres and all dependencies  
✅ Created complete dbt project structure  
✅ Configured database connection (profiles.yml template)  
✅ Created automation script for profiles setup  
✅ Wrote comprehensive documentation  
✅ Explained every technical decision and field  
✅ Prepared for transformation work (Day 2)

### Current Pipeline State

```
GitHub API → Python Ingestion → PostgreSQL (raw data) → dbt (ready to transform) → ???
```

**Week 1:** GitHub API → PostgreSQL ✅  
**Week 2 Day 1:** dbt infrastructure ✅  
**Week 2 Day 2+:** dbt transformations (next)  
**Week 4:** Streamlit dashboard (future)

### What You Need to Do Next

1. **Run the setup script:**
   ```powershell
   cd dbt_project
   .\setup_dbt_profile.ps1
   ```

2. **Update the password** in `~/.dbt/profiles.yml`

3. **Test the connection:**
   ```bash
   dbt debug
   ```

4. **Read README_SETUP.md** to understand the architecture

5. **Answer the interview questions** to test your understanding

Once `dbt debug` shows "All checks passed!", you're ready for Day 2!

---

**Status:** Week 2 Day 1 Complete ✅  
**Time Investment:** ~2 hours (setup + documentation)  
**Blocker:** None - ready to proceed to Day 2  
**Next Session:** Create first staging model (stg_push_events.sql)
