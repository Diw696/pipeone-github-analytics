# Week 2 Status Report

**Period:** July 1-10, 2026  
**Status:** ✅ Complete  
**Deliverables:** On Schedule

---

## Week Objective

Implement the transformation layer for the PipeOne data platform using dbt and PostgreSQL, moving from raw ingested data through Bronze and Silver layers with comprehensive data quality validation.

---

## Work Completed

### dbt Infrastructure (Day 1-2)

- Initialized dbt project with PostgreSQL profile
- Configured `dbt_project.yml` with profile name `pipeone`
- Created `setup_dbt_profile.ps1` for automated profile setup
- Established project structure: `models/staging/`, `models/silver/`, `tests/`

### Bronze Layer (Day 2)

- Created `models/staging/_sources.yml` with source definition for `github_raw_source`
- Configured `raw_events` source pointing to `public.github_events_raw` table
- Generated 6 auto-tests: freshness, row count validation, column presence checks
- Built `models/staging/stg_github_events.sql` as passthrough view with type casting
- Validated source dependencies and lineage

### Silver Layer (Day 3)

- Implemented `models/silver/int_push_events.sql`
  - Filters to PushEvent records
  - Extracts actor, commit metadata, branch reference
  - Uses defensive SQL (COALESCE) for null safety
  - Parses JSONB fields using `->` and `->>` operators

- Implemented `models/silver/int_pull_requests.sql`
  - Filters to PullRequestEvent records
  - Extracts PR metadata: action, author, title, pull request ID
  - Handles nested JSONB payloads consistently

- Both models use `{{ ref('stg_github_events') }}` for dependency tracking

### Data Quality Testing (Day 4)

**Schema Tests (13 total)**
- Created `models/silver/_schema.yml` with 13 column-level tests
- Unique constraints on `event_id` and `pull_request_id`
- Not-null validation on critical columns (`repo_name`, `actor_username`, `pr_action`)
- Accepted-values validation on categorical fields (`repo_name`, `pr_action`)
- Severity levels configured (error, warn) based on criticality

**Singular Tests (3 total)**
- `tests/no_future_timestamps.sql`: Ensures `fetched_at ≤ CURRENT_TIMESTAMP`
- `tests/push_model_integrity.sql`: Verifies only PushEvents in `int_push_events`
- `tests/no_negative_commit_count.sql`: Validates `commit_count ≥ 0`

**Automated Tests (6 total)**
- Source tests auto-generated from `_sources.yml`

**Total:** 26 tests, all passing (PASS=26, WARN=0, ERROR=0)

---

## Technical Achievements

### JSONB Parsing Strategy

Successfully extracted and flattened deeply nested GitHub event JSON:
- Used PostgreSQL `->` operator to navigate nested objects
- Used `->>` operator to extract final TEXT values
- Applied `jsonb_array_length()` for commit counts
- Implemented COALESCE for defensive null handling

Example: `raw_payload -> 'actor' ->> 'login'` extracts actor username from 3 levels deep.

### dbt Dependency Tracking

Established proper model dependencies:
```
github_raw_source → stg_github_events → int_push_events ┐
                                      → int_pull_requests ├→ Quality Tests
```

The `ref()` macro ensures models build in correct order and enables lineage visualization. `source()` macro documents external data and enables auto-generated tests.

### Data Quality Automation

Implemented multi-layered testing approach:
- Schema tests catch structural issues (duplicates, nulls, invalid values)
- Custom SQL tests enforce business rules (no future data, event type validation)
- Source tests validate external data freshness and integrity

All tests integrated into `dbt build` workflow—issues caught before production.

---

## Challenges Encountered

### Challenge 1: Circular Dependency in Documentation

**Issue:** Early test documentation referenced downstream models, creating logical loops.

**Resolution:** Restructured tests to validate only current model contents. Join upstream models only for lineage verification, not circular validation.

**Learning:** Test design must account for dependencies—tests shouldn't reference models that depend on them.

### Challenge 2: Optional Fields in PR Events

**Issue:** `pr_title` and `pr_author` are sometimes NULL in GitHub API responses.

**Resolution:** Changed `not_null` tests to `warn` severity instead of `error`. Missing fields don't block the pipeline but are logged for investigation.

**Learning:** Real-world data is messier than expected. Severity levels provide nuance—not all nulls are critical failures.

### Challenge 3: Ambiguous Column Names

**Issue:** `push_model_integrity` test joined models without explicit column aliases.

**Resolution:** Added table aliases and explicit join conditions for clarity.

**Learning:** Defensive SQL practices matter, even in test queries. Explicit is better than implicit.

---

## Key Technical Decisions

**JSONB Over Normalized Schema**  
Decision: Store raw events as JSONB instead of normalizing during ingestion.  
Rationale: Preserves flexibility for future schema changes, enables forensics, simplifies re-transformation.

**Three-Layer Medallion Architecture**  
Decision: Implement Bronze, Silver (implemented), and placeholder for Gold layers.  
Rationale: Progressive data refinement enables clear separation of concerns and easier debugging.

**PostgreSQL for Both Raw Storage and Transformation**  
Decision: Use single database system rather than separate data lake + warehouse.  
Rationale: Simpler architecture for learning project, PostgreSQL JSONB is production-quality, PostgreSQL supports SQL-based transformation natively.

**Extensive Test Coverage on Week 2**  
Decision: Implement 26 tests even though data volume is small.  
Rationale: Testing patterns established early scale better than retrofitted later, automated tests catch issues before they reach dashboards, demonstrates production practices.

---

## Lessons Learned

**dbt Compiles, PostgreSQL Executes**  
Initially thought dbt "runs" SQL directly. Reality: dbt first compiles Jinja2 templates into SQL, then sends compiled SQL to PostgreSQL for execution. This explains why we reference models via `ref()` and `source()` macros—they're template directives, not database functions.

**Medallion Architecture Clarity**  
Three layers seemed redundant until implementing them. Bronze preserves forensics, Silver standardizes for analysis, Gold optimizes for visualization. Each layer serves a distinct purpose. Skipping layers causes complexity to accumulate in a single place.

**Automated Testing Prevents "I Swear It Worked"**  
Manual verification works for small datasets. With 26 automated tests, we catch issues that would slip through manual checks. Tests become documentation—they explain what "correct" means.

**JSONB is More Practical Than It Looks**  
Initial concern: JSONB operators (`->`, `->>`) seemed complex. Actual usage: intuitive once you understand the difference (JSONB vs TEXT extraction). Defensive SQL with COALESCE makes it robust.

**Professionalism Through Documentation**  
ADRs, status reports, test documentation—these seem like overhead until reviewed. Mentor feedback showed these documents matter. They demonstrate thinking beyond code.

---

## Current Project Status

| Component | Status | Details |
|-----------|--------|---------|
| Ingestion | ✅ | Python client, GitHub API, PostgreSQL JSONB storage |
| Bronze Layer | ✅ | Source definitions, staging view, 6 auto-tests |
| Silver Layer | ✅ | int_push_events, int_pull_requests, 13 schema tests |
| Singular Tests | ✅ | 3 custom business validations |
| Data Quality | ✅ | 26/26 tests passing (PASS=26, WARN=0, ERROR=0) |
| dbt Lineage | ✅ | Dependency tracking, build ordering working |
| Documentation | ✅ | ADR, status report, test docs, updated README |
| **Gold Layer** | ⏳ | Planned for Week 3 |
| **Dashboard** | ⏳ | Planned for Week 4 |

---

## Next Week Plan (Week 3)

**Gold Layer Implementation**
- Fact table: `fct_daily_activity` (daily commits, PRs by repository)
- Dimension table: `dim_contributors` (unique contributors with metadata)
- Incremental model setup for scalability

**Metrics & Aggregation**
- Daily commit counts by repository
- PR velocity metrics (open/close times)
- Contributor activity aggregation

**Gold Layer Testing**
- Aggregate validation tests
- Grain tests (one row per day per repository)
- Completeness tests

**Week 3 Success Criteria**
- 10+ additional tests pass
- Gold tables queryable and documentable
- Incremental model pattern established

