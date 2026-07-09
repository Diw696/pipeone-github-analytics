/*
================================================================================
SINGULAR TEST: push_model_integrity
================================================================================

PURPOSE:
  Validate that int_push_events contains ONLY PushEvent records.
  
BUSINESS RULE:
  The int_push_events model filters to event_type = 'PushEvent' in its SQL.
  This test verifies the filter is working correctly.
  
WHY THIS MATTERS:
  - If filter breaks, non-PushEvents leak into the model
  - Downstream commit metrics become incorrect
  - commit_count field might be NULL (different event structure)
  - Dashboard shows wrong commit activity
  
EXPECTED RESULT:
  This query should return 0 rows (test passes).
  If it returns rows, those are non-PushEvent records that shouldn't be there.

FAILURE IMPACT:
  - Commit count aggregations include wrong events
  - Branch analysis includes irrelevant events
  - Could double-count activity (same event in multiple models)

REMEDIATION:
  If this test fails:
    1. Check int_push_events.sql WHERE clause
    2. Check upstream stg_github_events for data issues
    3. Investigate affected records: SELECT * FROM results of this query
    4. Verify event_type column is populated correctly

OWNER: Data Engineering Team
CREATED: Week 2 Day 4 (July 2026)

================================================================================
*/

-- Find all records in int_push_events that are NOT PushEvents
-- This should return 0 rows (if any rows, test fails)

select
    push_events.event_id,
    push_events.repo_name,
    staging.event_type,
    push_events.fetched_at
from {{ ref('int_push_events') }} as push_events
-- Join back to Bronze to get event_type for validation
inner join {{ ref('stg_github_events') }} as staging
    on push_events.event_id = staging.event_id
where staging.event_type != 'PushEvent'

/*
QUERY EXPLANATION:

1. Strategy:
   - int_push_events doesn't include event_type column (it's filtered out)
   - Join back to stg_github_events to retrieve event_type
   - Check if any records have wrong event_type

2. JOIN clause:
   inner join {{ ref('stg_github_events') }}
   on push_events.event_id = staging.event_id
   - Connects Silver back to Bronze using primary key
   - Retrieves event_type field for validation

3. WHERE clause:
   where staging.event_type != 'PushEvent'
   - Finds records that shouldn't be in int_push_events
   - Uses != (not <>) for PostgreSQL compatibility

WHY THIS TEST IS IMPORTANT:

Scenario: Someone accidentally changes int_push_events.sql

-- Before (correct):
where event_type = 'PushEvent'

-- After (broken):
where event_type = 'PushEvent' OR event_type = 'PullRequestEvent'  -- Oops!

Without this test:
  ✗ Bug goes unnoticed
  ✗ Commit metrics include PR events (wrong!)
  ✗ Dashboard shows inflated commit activity
  ✗ Business makes decisions on bad data

With this test:
  ✓ Test fails immediately
  ✓ dbt build stops before deploying
  ✓ Developer sees error: "push_model_integrity failed"
  ✓ Fix is made before production

TEST SCENARIOS:

Pass: Returns 0 rows
  ✓ All records in int_push_events are PushEvents
  ✓ Filter is working correctly
  ✓ No data integrity issues

Fail: Returns rows
  ✗ Example output:
    event_id  | repo_name        | event_type          | fetched_at
    ----------|------------------|---------------------|-------------------
    789012... | facebook/react   | PullRequestEvent    | 2026-07-09 10:00:00
  
  ✗ Action: A PullRequestEvent leaked into int_push_events!
            Check the WHERE clause in int_push_events.sql
*/
