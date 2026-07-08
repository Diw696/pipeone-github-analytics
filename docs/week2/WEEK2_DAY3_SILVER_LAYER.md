# Week 2 – Day 3: Silver Layer (JSONB Transformation)

**Status:** ✅ Completed

## Objective

Transform the Bronze staging data into event-specific Silver models by extracting useful information from the GitHub JSONB payload.

---

## Work Completed

### Created Silver Models

- `models/silver/int_push_events.sql`
- `models/silver/int_pull_requests.sql`

### Implemented

- Read data from `stg_github_events` using the `{{ ref() }}` macro.
- Filtered records based on event type.
- Extracted nested JSONB fields using PostgreSQL operators (`->` and `->>`).
- Used `COALESCE()` to safely handle missing commit arrays.
- Configured the Silver models as **Views** in `dbt_project.yml`.

---

## Verification

Successfully executed the following commands:

```bash
dbt ls
dbt parse
dbt run
```

Result:

- `stg_github_events`
- `int_push_events`
- `int_pull_requests`

were successfully created in PostgreSQL.

---

## Output Validation

Verified the generated models using SQL:

```sql
SELECT * FROM int_push_events LIMIT 10;
```

```sql
SELECT * FROM int_pull_requests LIMIT 10;
```

### Observations

- Push events correctly expose actor username, branch reference and commit count.
- Pull request events expose action and pull request ID.
- Some fields such as `pr_title` and `pr_author` return `NULL` because they are not present in the current GitHub API payload. This is expected behavior and the models will automatically populate these fields whenever the source data contains them.

---

## Key Concepts Learned

- Difference between the Bronze and Silver layers.
- Using PostgreSQL JSONB operators (`->` and `->>`).
- Creating model dependencies with `ref()`.
- Handling missing values safely using `COALESCE()`.
- Building modular transformation models with dbt.

---

## Next Step

Build the **Gold Layer**, where Silver models will be aggregated into analytics-ready tables for reporting and dashboards.