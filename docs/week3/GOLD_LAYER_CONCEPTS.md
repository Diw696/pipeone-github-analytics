# Week 3: Gold Layer - 12 Core Concepts (Viva Preparation)

## Topic 1: Why Does a Gold Layer Exist?

**Simple Explanation:**
The Gold layer is where we prepare data for dashboards. Instead of running complex calculations every time someone opens a dashboard, we pre-compute everything once and store it. This makes dashboards fast and reliable.

**Example:** 
- Without Gold layer: Dashboard queries 10K raw events, groups by repo and date, calculates sums → takes 10 seconds
- With Gold layer: Dashboard queries 1K pre-aggregated rows → takes 100ms

**Professional Explanation:**
The Gold layer implements the transformation-as-you-go (TAIYG) principle in ELT (Extract-Load-Transform). Rather than deferring all transformations to query time (pushing logic to BI tools), we materialize business-ready aggregations as tables. This:

1. **Separates concerns**: Analysts don't need to understand how to aggregate events
2. **Centralizes logic**: Business rules live in dbt (version control, testing, documentation)
3. **Enables governance**: Data quality tests catch issues before dashboards render them
4. **Reduces latency**: Pre-computed aggregates query in milliseconds vs seconds
5. **Supports incremental loading**: Can update only changed dates, not recompute everything

**When to use Gold vs when to push to BI:** Gold layer for metrics used repeatedly across multiple dashboards or reports. BI-layer transformations for one-off, exploratory analysis.

---

## Topic 2: Difference Between Bronze, Silver, and Gold

**Simple Explanation:**

| Layer | What | Example |
|-------|------|---------|
| **Bronze** | Raw data as-is from source | JSON events from GitHub API |
| **Silver** | Parsed and typed, one event type per model | Separate tables for PushEvent vs PullRequestEvent |
| **Gold** | Aggregated for business use | Daily metrics by repo, contributor profiles |

**Bronze Layer Purpose:**
- Store data exactly as received
- Enable audit trail (what did the source system actually send?)
- Support re-processing if parsing logic changes

**Silver Layer Purpose:**
- Flatten JSONB into typed columns
- One row per event (same as Bronze, but cleaner)
- Enable analysts to use simple SQL without JSON operators

**Gold Layer Purpose:**
- Pre-aggregate for dashboards
- One row per business entity + time period (e.g., repo + date)
- Support drill-down and filtering

**Professional Comparison:**

| Aspect | Bronze | Silver | Gold |
|--------|--------|--------|------|
| Grain | Event | Event | Aggregated (repo+date, contrib+repo+date) |
| Storage | JSONB (unstructured) | Typed columns (structured) | Denormalized star schema |
| Purpose | Audit trail | Intermediate processing | Business reporting |
| Update frequency | Continuous | Continuous | Daily (batch) |
| Row count | High (~10K events) | High (~10K events) | Low (~1K-200K aggregates) |
| Typical query time | 5-10s | 2-5s | <500ms |

---

## Topic 3: What is a Fact Table?

**Simple Explanation:**
A fact table stores measurable events or transactions. Each row represents "something happened": a commit was pushed, a PR was opened, etc. Fact tables contain numbers you can add up (metrics).

**Example - Fact Table Row:**
```
repo_id: 'abc123...'
activity_date: 2026-07-13
push_count: 5
commit_count: 18
pr_event_count: 3
pr_merged: 2
```

This says: "On July 13, facebook/react had 5 pushes (18 commits) and 3 PR events (2 merged)."

**Key Characteristics:**
1. **Foreign keys**: Links to dimensions (repo_id, contrib_id)
2. **Additive metrics**: push_count, commit_count can be summed and averaged
3. **Grain**: One row per (repo, date) or (contributor, repo, date)
4. **Immutable**: Once a day closes, metrics don't change (or use SCD Type 2)

**Professional Explanation:**
Facts are the intersection of dimensions at a specific grain. In our model:
- `fct_github_daily_activity`: Grain = (repository, date). Metrics: push_count, commit_count, pr_event_count, etc.
- `fct_contributor_daily_activity`: Grain = (contributor, repository, date). Same metrics, but per-contributor-per-repo.

**Why Two Facts?**
- Different grains answer different questions
- fct_github_daily_activity: "Was facebook/react active on July 13?" (1K rows, fast dashboard)
- fct_contributor_daily_activity: "Which contributor was most active in react on July 13?" (enables drill-down)

**Types of Fact Tables (FYI):**
1. **Transaction facts**: Grain = one row per transaction (sales order, delivery)
2. **Periodic snapshot facts**: Grain = one row per entity + period (account balance on each month-end)
3. **Accumulating snapshot facts**: One row per process lifetime (order from creation to delivery)

Our fact tables are **periodic snapshots** (daily grain).

---

## Topic 4: What is a Dimension Table?

**Simple Explanation:**
A dimension table stores attributes about entities. Dimensions are the "who", "what", "where", "when" that you filter and group by. If fact metrics are numbers, dimensions are labels.

**Example - Dimension Table Row:**
```
repo_id: 'abc123...'
repo_name: 'facebook/react'
owner: 'facebook'
language: 'JavaScript'
stars: 225000
total_pushes: 2500 (cumulative metric, denormalized)
```

This describes: "facebook/react is a JavaScript repo owned by facebook with 225K stars."

**Key Characteristics:**
1. **Surrogate keys**: System-generated IDs (repo_id) for fast JOINs
2. **Business keys**: Natural identifiers (repo_name) for tracing and verification
3. **Descriptive attributes**: Not metrics, but properties (language, owner)
4. **Slowly changing**: Metadata changes slowly (repo language stays same for years)

**Professional Explanation:**
Dimensions contextualize facts. They answer "what does this number represent?" 
- `dim_repository`: Repository attributes (owner, language, stars) + cumulative activity summary
- `dim_contributor`: Contributor attributes (username, type: push_only/pr_only/both) + cumulative stats

**Why Denormalize?**
Normal form would be:
```
Repository:
  repo_id, repo_name, owner, language

Repository_Stats:
  repo_id, total_pushes, total_commits, total_pr_events
```

But in Gold layer, we combine them (denormalize) because:
1. **Rare updates**: Once loaded, stats don't change until next run
2. **Single JOIN instead of two**: Faster queries
3. **Easier understanding**: All repo info in one place

This trade-off is appropriate for analytical (OLAP) systems. OLTP systems (transactional) avoid denormalization.

---

## Topic 5: What is Table Grain, and Why Decide Before Writing SQL?

**Simple Explanation:**
Grain is "one row per WHAT?" If you can't answer this, your data model is broken.

**Examples:**
- `dim_repository` grain: "one row per repository" (repo_name is unique key)
- `fct_github_daily_activity` grain: "one row per (repo, date)" combination
- `fct_contributor_daily_activity` grain: "one row per (contributor, repo, date)"

**Why Decide First?**
1. **Defines aggregation level**: If you want "one row per (contributor, repo, date)", you must GROUP BY all three
2. **Prevents duplicates**: Wrong grain creates duplicate rows (data quality issue)
3. **Determines metric meaning**: "commit_count" means different things at different grains:
   - At (repo, date): Total commits for this repo on this date
   - At (contributor, repo, date): Total commits by this contributor for this repo on this date

**Example of Wrong Grain:**
```sql
-- WRONG: Forgot to group by activity_date
SELECT 
    repo_name,
    SUM(commit_count) as total_commits  -- Groups by repo only
FROM fct_github_daily_activity
GROUP BY repo_name

-- Result: Duplicates! (One row per repo, summarizing all dates into one number)
-- Should be: GROUP BY repo_name, activity_date
```

**Professional Explanation:**
Grain must be **declared and enforced** via unique constraints:
```sql
ALTER TABLE fct_github_daily_activity
ADD CONSTRAINT unique_daily_activity UNIQUE (repo_id, activity_date);
```

This constraint ensures:
- No two rows for the same (repo, date) pair
- If you try to insert a duplicate, PostgreSQL rejects it with error
- Data quality test: `unique` test on grain columns

**Grain Decision Matrix (for our project):**

| Question | Answer | Grain | Row Count |
|----------|--------|-------|-----------|
| Overall daily activity? | "How active was each repo each day?" | (repo, date) | 1,095 |
| Contributor breakdown? | "Which contributor did what in which repo when?" | (contributor, repo, date) | 100K-200K |
| Repository profile? | "General info about each repo?" | (repo) | 3 |
| Contributor profile? | "General info about each contributor?" | (contributor) | 100-200 |

We chose these grains because they answer different dashboard questions without forcing unnecessary JOIN complexity.



## Topic 6: Star Schema vs Snowflake Schema

**Simple Explanation:**
- **Star Schema**: Facts in center, dimensions around them like a star. Simple JOINs.
- **Snowflake Schema**: Dimensions are themselves normalized (sub-dimensions). More JOINs, more complex.

**Visual Comparison:**

```
STAR SCHEMA (Our Choice):
                    dim_repository
                          |
                          | repo_id (FK)
                          |
fct_github_daily_activity---dim_contributor
                          |
                          | contrib_id (FK)

Facts join directly to dimensions. Query needs 2 JOINs.


SNOWFLAKE SCHEMA (More Complex):
       dim_owner  dim_language       dim_contributor_type
            |           |                    |
            |           |                    |
       ----+------- dim_repository      ----+----
            |
fct_github_daily_activity---dim_contributor
                          |
                          | (more intermediate tables)

Facts still join to dimensions, but dimensions link to sub-dimensions.
Query might need 4+ JOINs.
```

**Star Schema Pros:**
- Simple: Few JOINs
- Fast: Less work for query optimizer
- Readable: Analysts understand structure quickly
- Appropriate for small teams/datasets

**Star Schema Cons:**
- Denormalized: Some data redundancy (e.g., repo_name appears in both dim_repository and fact)
- SCD complexity: If repo attributes change, must handle carefully

**Snowflake Schema Pros:**
- Normalized: Less redundancy
- Smaller dimensions: Sub-dimensions deduplicated
- Scalable: If you have 1,000 repositories with 100 languages, snowflake saves space

**Snowflake Schema Cons:**
- More JOINs: Query slower
- Complex: Harder to understand and maintain
- Overkill for small datasets: If you only have 3 repos, snowflake gains nothing

**Our Decision: Star Schema**

Why? 
1. We have **3 repositories, 100-200 contributors**: Small dimensions, no need to normalize
2. **Analytics workload**: Speed matters, normalization doesn't help enough
3. **Team size**: Smaller team, simpler schema = fewer bugs
4. **Future-proof**: Can upgrade to Snowflake if dataset grows to 10K repos, but unlikely

**Professional Decision Framework:**

Use **Star Schema** when:
- Dimensions are small (<10K rows)
- Analytics team small (<5 people)
- Query speed critical
- Maintenance simplicity valued

Use **Snowflake Schema** when:
- Dimensions are huge (1M+ rows)
- Many dimension hierarchies (Organization → Department → Team)
- Data warehouse team large, mature
- Complex reporting requirements (drill-down across hierarchies)

---

## Topic 7: OLTP vs OLAP

**Simple Explanation:**
- **OLTP** (Online Transaction Processing): Handles individual transactions fast. Example: Bank ATM (insert 1 deposit, update 1 account)
- **OLAP** (Online Analytical Processing): Analyzes large datasets. Example: "Show me all deposits over $10K from all accounts in 2026"

**OLTP Example - Bank:**
```sql
-- OLTP: Fast insert (1 transaction)
INSERT INTO account_transactions (account_id, amount, type)
VALUES (12345, 500, 'deposit')

UPDATE accounts SET balance = balance + 500
WHERE account_id = 12345
```

**OLAP Example - Bank:**
```sql
-- OLAP: Scan entire table, aggregate
SELECT 
    account_type,
    SUM(amount) as total_deposits,
    COUNT(*) as transaction_count,
    AVG(amount) as avg_deposit
FROM account_transactions
WHERE type = 'deposit' AND year = 2026
GROUP BY account_type
```

**OLTP vs OLAP Comparison:**

| Aspect | OLTP | OLAP |
|--------|------|------|
| **Use Case** | Operational (handle orders, payments) | Analytical (reports, dashboards) |
| **Query Pattern** | Insert/Update 1-100 rows | Scan 1M+ rows, aggregate |
| **Latency Target** | <100ms | <5s (usually BI tools cache) |
| **Schema** | Normalized (3NF) | Denormalized (star/snowflake) |
| **Transactions** | ACID required | Eventual consistency OK |
| **Examples** | MySQL, PostgreSQL (production DBs) | Snowflake, BigQuery, Redshift |
| **Indexing** | B-tree on frequently filtered cols | Columnar compression, partitioning |

**Where PipeOne Fits:**
- GitHub API → PostgreSQL = OLTP tool (but used for analytics)
- Bronze layer = OLTP style (immutable log of events)
- Silver layer = Transitional (event transformation)
- Gold layer = **OLAP style** (aggregated, denormalized, analytics-ready)

**Key Insight:**
PostgreSQL can do both OLTP and OLAP, but it's optimized for OLTP. For true OLAP at scale (TB+ data), we'd use Snowflake or BigQuery. For our dataset (<1MB Gold layer), PostgreSQL handles both well.

**Implications for Our Design:**

✅ **OLAP-appropriate choices:**
- Denormalized star schema (fct_github_daily_activity has all info you need)
- Pre-aggregated metrics (no SUM/COUNT at query time)
- Repeatable data (same facts stay same until next ETL run)

✅ **Avoid OLTP patterns:**
- No transactional consistency needed (one person writing dashboard won't interfere with another)
- No row-level locking needed
- Historical data preserved (no UPDATE of past records, only INSERT new periods)

---

## Topic 8: Business Keys vs Surrogate Keys

**Simple Explanation:**
- **Business Key**: Human-readable identifier (repo_name = 'facebook/react')
- **Surrogate Key**: System-generated ID (repo_id = 'abc123...')

**Example:**
```
Business Key: repo_name = 'facebook/react' (you can say this to another human)
Surrogate Key: repo_id = md5('facebook/react|2026-07-13') = 'abc123...' (system ID)
```

**Business Key Purpose:**
- Verification: "Does this row belong to facebook/react?"
- Traceability: "Show me all rows with repo_name = 'microsoft/vscode'"
- Joins: Can link fact to dimension using repo_name directly
- Debugging: SQL query result shows meaningful data

**Surrogate Key Purpose:**
- Performance: Integer (or short hash) JOINs are faster than string JOINs
- Stability: If business key changes, surrogate key stays same (supports SCD)
- Uniqueness: System-guaranteed to be unique (no accidental duplicates)
- Referential integrity: Foreign key constraints work reliably

**Why Both?**

| Challenge | Using Business Key Only | Using Surrogate Key Only | Using Both |
|-----------|------------------------|-------------------------|-----------|
| Speed | Slow JOINs (string compare) | N/A | Fast (short hash JOINs) |
| Verification | Can verify facts | Can't trace which repo | ✅ Can trace via business key |
| Debugging | Easy (see repo_name) | Hard (see only ID) | ✅ Both available |
| Slowly Changing Dims | Business key might change | Need to track history | ✅ Surrogate key tracks changes |

**Concrete Example:**

```sql
-- Query without business key (hard to verify):
SELECT SUM(commits_in_pushes)
FROM fct_contributor_daily_activity
WHERE contrib_id = '9f8e7d6c...'  -- Who is this?

-- Query with business key (easy to verify):
SELECT SUM(commits_in_pushes)
FROM fct_contributor_daily_activity
WHERE username = 'alice'  -- Clear!

-- Query using both (efficient AND clear):
SELECT SUM(commits_in_pushes)
FROM fct_contributor_daily_activity
WHERE contrib_id = (SELECT contrib_id FROM dim_contributor WHERE username = 'alice')
-- Or with explicit reference for debugging:
SELECT f.* FROM fct_contributor_daily_activity f
JOIN dim_contributor d ON f.contrib_id = d.contrib_id
WHERE d.username = 'alice'
```

**Professional Best Practice:**
1. **Always include both keys** in dimensions
2. **Use surrogate keys for JOINs** in facts (performance)
3. **Include business keys in facts** for verification (denormalized, but worth the redundancy)
4. **Test referential integrity**: Every surrogate key in fact must exist in dimension

---

## Topic 9: Why Dashboards Should Read Gold Instead of Silver

**Simple Explanation:**
Reading from Silver (events) makes dashboards slow. Reading from Gold (aggregates) makes them fast.

**Performance Comparison:**

```
Dashboard Query: "Show me daily pushes for facebook/react for the last 30 days"

OPTION 1 - Read Silver (Wrong):
SELECT 
    fetched_at::date as date,
    COUNT(*) as push_count,
    SUM(commit_count) as commits
FROM int_push_events
WHERE repo_name = 'facebook/react'
  AND fetched_at::date >= CURRENT_DATE - 30
GROUP BY fetched_at::date
ORDER BY fetched_at::date

-- Performance: ~5,000 rows scanned (30 days × ~170 pushes/day)
-- Aggregation: GROUP BY happens at query time
-- Time: 2-5 seconds (has to read, parse, aggregate)

OPTION 2 - Read Gold (Correct):
SELECT 
    activity_date,
    push_count,
    commit_count
FROM fct_github_daily_activity
WHERE repo_name = 'facebook/react'
  AND activity_date >= CURRENT_DATE - 30
ORDER BY activity_date

-- Performance: ~30 rows scanned (exactly what you need)
-- Aggregation: Already done, just read pre-computed values
-- Time: <100ms (simple table scan)
```

**Speed Improvement: 50x faster with Gold!**

**Why This Matters for Dashboards:**
1. **User Experience**: 5 seconds feels slow, <100ms feels instant
2. **Scalability**: If 10 users view dashboard at same time:
   - Silver approach: 10 queries × 5s = 50s total (people wait a long time)
   - Gold approach: 10 queries × 100ms = 1s total (snappy)
3. **Resource Efficiency**: 50x fewer rows processed = 50x less CPU, memory, I/O
4. **Predictability**: Pre-aggregated metrics don't depend on data volume (stable latency)

**What Changes Can Break This?**
- If new events arrive and Silver changes, Gold is stale (solved by incremental loading)
- If business logic changes (e.g., "don't count bots as contributors"), must rebuild Gold

**Professional Decision:**
Gold layer is appropriate when:
✅ Metrics are repeated (used in multiple dashboards)
✅ Data volume is high (10K+ events)
✅ Query latency matters (<1 second required)
✅ Metrics are stable (don't change every day)

Gold layer is overkill when:
❌ One-time exploratory queries (use Silver directly)
❌ Rarely used metrics (can compute on demand)
❌ Highly volatile metrics (would need updating every minute)

---

## Topic 10: Why Aggregations Belong Inside the Warehouse Instead of Power BI or Streamlit

**Simple Explanation:**
If your BI tool does `GROUP BY repo_name, SUM(commits)`, you're making the BI tool do work that should be in the warehouse.

**Anti-Pattern Example (BI Tool Does Aggregation):**

```
Power BI Dashboard: "Daily Commits by Repo"

Power BI Query (Wrong):
SELECT repo_name, fetched_at, commit_count
FROM fct_github_daily_activity
-- No aggregation! BI tool will GROUP BY itself

BI Tool Processing:
1. Load 1,095 rows (3 repos × 365 days)
2. Aggregate: GROUP BY repo_name, fetched_at::date
3. Render: Show 3 lines (one per repo)

Problem:
- BI tool is good at rendering (charting), not aggregation
- If 100 Power BI users view same dashboard, each runs this query independently
- BI tool queries are often not cached (each refresh hits database)
- Hard to test aggregation logic (buried in BI tool, not version-controlled)
```

**Pattern (Warehouse Does Aggregation - Correct):**

```
Power BI Dashboard: "Daily Commits by Repo"

Power BI Query (Correct):
SELECT repo_name, activity_date, commit_count
FROM fct_github_daily_activity

BI Tool Processing:
1. Load 1,095 rows (already aggregated exactly what we need)
2. Render: Show 3 lines (one per repo)

Benefits:
- Query is simple: BI tool focuses on rendering
- Aggregation logic in dbt (version-controlled, tested)
- BI tool scales easily (just rendering)
- All users get same results (no recomputation)
```

**Why This Matters:**

| Aspect | Aggregation in BI | Aggregation in Warehouse |
|--------|------------------|--------------------------|
| **Testing** | Hard (no test framework) | Easy (dbt tests) |
| **Audit Trail** | Buried in BI tool | Version-controlled in dbt |
| **Performance** | Depends on BI tool capability | Optimized SQL (indexes) |
| **Consistency** | Might differ per BI tool | One source of truth |
| **Caching** | BI tool-dependent | Materialized table (cache by default) |
| **Scale** | Slower with more users | No change (all users read same pre-computed table) |

**Separation of Concerns:**
- **Warehouse (dbt)**: Responsible for accuracy, logic, testing
- **BI Tool (Power BI/Streamlit)**: Responsible for visualization, interactivity

```
If BI tool does aggregation:
  BI Tool = "Do I multiply by 2 or 3?" (shouldn't have to know)
  
If Warehouse does aggregation:
  BI Tool = "Show me these numbers beautifully" (what it's built for)
  Warehouse = "Here are the correct numbers" (what it's built for)
```

**Professional Practice:**
1. **Compute-heavy logic → dbt (warehouse)**
2. **Rendering-heavy logic → Power BI (BI tool)**
3. **Never have both aggregate** (one source of truth)

---

## Topic 11: How Dimensional Modeling Improves Query Performance

**Simple Explanation:**
Dimensional modeling (star schema) makes queries faster by:
1. **Reducing joins**: Direct links from facts to dimensions (not through normalized chains)
2. **Enabling indexes**: Integer (or short hash) surrogate keys are index-friendly
3. **Denormalizing smart**: Include needed attributes without duplicating everything

**Performance Analysis - Before & After Dimensional Model:**

```
BEFORE (Normalized, if we had it):
tables:
  - events (10K rows: push events + PR events mixed)
  - repositories (3 rows)
  - contributors (100 rows)

Query: "Show commits by repo for July 13"
SELECT 
    r.repo_name,
    COUNT(*) as count
FROM events e
JOIN repositories r ON e.repo_id = r.id
WHERE e.event_type = 'PushEvent'
  AND e.activity_date = '2026-07-13'
GROUP BY r.repo_name

Issues:
- 10K rows scanned (includes PR events, irrelevant)
- JOIN adds cost (even though only 3 repos)
- GROUP BY on string (repo_name) slower than integer

AFTER (Dimensional Model):
tables:
  - fct_github_daily_activity (1,095 rows: pre-filtered by date, pre-filtered by type, pre-aggregated)
  - dim_repository (3 rows)

Query: "Show commits by repo for July 13"
SELECT 
    repo_name,
    commit_count as count
FROM fct_github_daily_activity
WHERE activity_date = '2026-07-13'

Benefits:
- 3 rows scanned exactly (3 repos, 1 day)
- No JOIN needed (repo_name denormalized)
- No GROUP BY (already aggregated)
- No type filtering (only push events in this table)

Speed gain: 10K→3 = 3,333x fewer rows
```

**Why Dimensional Modeling Wins:**

1. **Grain Reduction**: Pre-aggregate to coarser granularity (events → daily)
   - 10K raw events → 1K daily aggregates
   - Query scans 1K instead of 10K (10x faster)

2. **Integer JOINs**: Surrogate keys are small, indexed
   - `repo_id = 'abc123'` (32 chars, slow string compare)
   - vs potential integer (4 bytes, fast numeric compare)
   - In PostgreSQL, text indexes are slower than integer indexes

3. **Denormalization**: Keep attributes you filter/group by in fact table
   - No need to JOIN dim_repository just to see repo_name
   - Saves one JOIN operation per query

4. **Indexes**: Materialized tables can have strategic indexes
   - `CREATE INDEX idx_daily_activity_date ON fct_github_daily_activity(activity_date DESC)`
   - Queries filtering by date become even faster

**The Trade-Off:**

| Dimension Model | Normalized Model |
|---|---|
| Faster queries | Slower queries |
| More storage (denormalized) | Less storage (normalized) |
| Easier to understand | More complex joins |
| Better for OLAP (analytics) | Better for OLTP (transactional) |

For analytics, speed of reading >> storage savings. Gold layer accepts the trade-off.

---

## Topic 12: How This Architecture Scales from Thousands to Millions of GitHub Events

**Simple Explanation:**
As data grows, we can keep Gold layer fast by partitioning and incremental loading. Facts stay queried quickly even with 10M events.

**Growth Scenario:**

```
Today (Week 3):
- Events: 10K (3 repos × 365 days × ~10 events/day)
- fct_github_daily_activity: 1K rows (3 repos × 365 days)
- Query time: <100ms

Year 2 (Growing):
- Events: 3.6M (adding 100 repos)
- fct_github_daily_activity: 36.5K rows (100 repos × 365 days)
- Query time: ~200ms (still <500ms)

Year 3 (Mature):
- Events: 36M (adding 1,000 repos)
- fct_github_daily_activity: 365K rows (1,000 repos × 365 days)
- Query time: ~500ms-1s (might need optimization)
```

**How to Keep Fast Despite Growth:**

1. **Partitioning by Date**
```sql
-- PostgreSQL table partitioned by date range
CREATE TABLE fct_github_daily_activity (
    repo_id text,
    activity_date date,
    commit_count integer,
    ...
) PARTITION BY RANGE (activity_date)

-- Each month's data in separate partition
CREATE TABLE fct_github_daily_activity_2026_01 
  PARTITION OF fct_github_daily_activity
  FOR VALUES FROM ('2026-01-01') TO ('2026-02-01')

-- Query benefits: Only scans needed partition
-- "Show July 2026 data" → Only scans July partition, ignores January-June
```

2. **Incremental Loading**
```sql
-- Instead of rebuilding entire table daily:
-- DELETE yesterday + today's data, re-INSERT fresh data

DELETE FROM fct_github_daily_activity
WHERE activity_date >= CURRENT_DATE - 1

INSERT INTO fct_github_daily_activity
SELECT ... WHERE activity_date >= CURRENT_DATE - 1
-- Only processes 2 days of events, not 10M total events
-- Time: O(2 days) instead of O(all history) = 180x faster!
```

3. **Indexing Strategy**
```sql
-- Create strategic indexes as data grows
CREATE INDEX idx_fct_daily_repo_date 
  ON fct_github_daily_activity(repo_id, activity_date DESC)

CREATE INDEX idx_fct_daily_date 
  ON fct_github_daily_activity(activity_date DESC)

-- With these indexes:
-- "Show all repos for last 7 days" → Uses idx_fct_daily_date
-- "Show repo X for year 2026" → Uses idx_fct_daily_repo_date
-- Query planner picks best index automatically
```

4. **Columnar Compression** (future, if using Snowflake/BigQuery)
```
PostgreSQL stores rows (row-oriented): Each row stored together
- Good for OLTP (insert 1 row)
- Bad for OLAP (SUM all commits) - loads unnecessary columns

Snowflake stores columns (columnar): Each column stored together
- Bad for OLTP (must read all columns)
- Good for OLAP (read only commit_count column) - 10x compression

For PipeOne, PostgreSQL suffices now. If we move to Snowflake (millions of rows),
get columnar compression automatically.
```

**Expected Performance at Scale:**

| Events | Daily Rows | Query Time |  Notes |
|--------|------------|-----------|--------|
| 10K (Week 3) | 1K | <100ms | All in memory |
| 3.6M (100 repos) | 36.5K | <200ms | Still fast, partitioning not needed yet |
| 36M (1K repos) | 365K | 500ms-1s | Partitioning + indexes essential |
| 360M (10K repos) | 3.6M | 1-3s | Might move to BigQuery/Snowflake |

**Key Insight:**
The Gold layer architecture is designed to scale from thousands to billions of events. As long as we:
1. Keep grain coarse (daily, not hourly)
2. Use incremental loading (not full refresh)
3. Add indexes as needed
4. Partition by date

...queries stay fast indefinitely, even with massive data volumes.

---

## Summary: 12 Topics Recap

| # | Topic | Key Takeaway |
|---|-------|--------------|
| 1 | Why Gold Exists | Pre-compute for speed (50x faster queries) |
| 2 | Bronze-Silver-Gold | Raw → Parsed → Aggregated |
| 3 | Fact Tables | Measurable events with foreign keys |
| 4 | Dimension Tables | Attributes with business + surrogate keys |
| 5 | Table Grain | Decide grain first (one row per WHAT?) |
| 6 | Star vs Snowflake | Star simpler for small datasets (ours) |
| 7 | OLTP vs OLAP | Gold layer is OLAP (aggregate, analyze) |
| 8 | Keys | Both business (traceability) + surrogate (speed) |
| 9 | Dashboards use Gold | Faster, consistent, maintainable |
| 10 | Warehouse aggregates | dbt (logic), BI (rendering) |
| 11 | Dimensional perf | Grain reduction + denormalization = fast |
| 12 | Scaling | Partitioning + incremental loading + indexes |

All 12 concepts are implemented in PipeOne's Gold layer. You can now explain them to your mentor!

