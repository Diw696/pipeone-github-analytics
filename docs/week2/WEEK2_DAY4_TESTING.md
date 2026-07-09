# Week 2 – Day 4: Data Quality & Testing

**Status:** ✅ Completed

---

## Objective

Implement automated data quality validation for the Bronze and Silver layers using dbt schema tests and custom SQL tests.

---

## Work Completed

### Schema Tests

Created `models/silver/_schema.yml` with automated validation rules.

Implemented tests for:

- `unique`
- `not_null`
- `accepted_values`

Validated key fields such as:

- `event_id`
- `pull_request_id`
- `repo_name`
- `pr_action`
- `commit_count`

---

### Custom SQL Tests

Created three business-rule validations inside the `tests/` directory.

| Test | Purpose |
|------|---------|
| `no_future_timestamps.sql` | Ensure `fetched_at` never contains future timestamps |
| `push_model_integrity.sql` | Verify `int_push_events` contains only `PushEvent` records |
| `no_negative_commit_count.sql` | Ensure commit counts are never negative |

---

## Validation

Executed:

```bash
dbt run
dbt test
dbt build
```

Final Result:

```text
PASS = 26
WARN = 0
ERROR = 0
SKIP = 0
```

All models and automated data quality tests completed successfully.

---

## Issues Resolved

During validation, the following issues were identified and fixed:

- Fixed an ambiguous column reference in `push_model_integrity.sql`.
- Updated the accepted Pull Request action from `merge` to `merged`.
- Removed unnecessary `not_null` tests for optional fields (`pr_title` and `pr_author`) after confirming the GitHub API does not always provide these values.

After applying these fixes, all 26 tests passed successfully.

---

## Key Concepts Learned

- Difference between Schema Tests and Singular Tests.
- Using dbt to automate data validation.
- Applying business-rule testing with custom SQL.
- Understanding `dbt run`, `dbt test`, and `dbt build`.
- Investigating and resolving failing data quality tests.

---

## Pipeline Status

```
GitHub API
      │
      ▼
github_events_raw
      │
      ▼
stg_github_events
      │
      ├───────────────┐
      ▼               ▼
int_push_events   int_pull_requests
      │
      ▼
26 Automated Data Quality Tests
      │
      ▼
✔ PASS
```

---

## Next Step

Generate dbt documentation and lineage using:

```bash
dbt docs generate
dbt docs serve
```

This will provide an interactive visualization of the project architecture and model dependencies for the Week 2 presentation.