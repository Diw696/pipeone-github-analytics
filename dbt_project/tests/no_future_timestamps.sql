/*
================================================================================
SINGULAR TEST: no_future_timestamps
================================================================================

PURPOSE:
  Validate that fetched_at timestamps are never in the future.
  
BUSINESS RULE:
  Our ingestion pipeline fetches historical events from GitHub API.
  It is physically impossible for fetched_at to be greater than CURRENT_TIMESTAMP.
  
WHY THIS MATTERS:
  - Future timestamps break time-series analysis
  - Indicates system clock issues (server time misconfigured)
  - Could indicate data corruption or API issues
  
EXPECTED RESULT:
  This query should return 0 rows (test passes).
  If it returns rows, those records have invalid future timestamps (test fails).

FAILURE IMPACT:
  - Daily aggregations show events in wrong date buckets
  - Freshness checks give false positives
  - Dashboards show "activity tomorrow" (confusing for users)

REMEDIATION:
  If this test fails:
    1. Check server time: Is the database server clock correct?
    2. Check ingestion code: Is timezone handling correct?
    3. Check API response: Is GitHub returning future timestamps?
    4. Investigate affected records: SELECT * FROM results of this query

OWNER: Data Engineering Team
CREATED: Week 2 Day 4 (July 2026)

================================================================================
*/

-- Find all records where fetched_at is in the future
-- This should return 0 rows (if any rows, test fails)

-- Check Push Events
select
    'int_push_events' as model_name,
    event_id,
    repo_name,
    fetched_at,
    current_timestamp as current_time,
    fetched_at - current_timestamp as time_difference
from {{ ref('int_push_events') }}
where fetched_at > current_timestamp

union all

-- Check Pull Request Events
select
    'int_pull_requests' as model_name,
    event_id,
    repo_name,
    fetched_at,
    current_timestamp as current_time,
    fetched_at - current_timestamp as time_difference
from {{ ref('int_pull_requests') }}
where fetched_at > current_timestamp

/*
QUERY EXPLANATION:

1. SELECT clause includes:
   - model_name: Which Silver model has the issue
   - event_id: Identifier for the bad record
   - fetched_at: The invalid future timestamp
   - current_timestamp: Current time for comparison
   - time_difference: How far in the future (for debugging)

2. WHERE clause:
   fetched_at > current_timestamp
   - Finds records where ingestion time is after current time
   - Uses > (not >=) because exactly current_timestamp is valid

3. UNION ALL:
   - Combines results from both Silver models
   - Checks all models with fetched_at column in one test

TEST SCENARIOS:

Pass: Returns 0 rows
  ✓ All fetched_at values are in the past
  ✓ System time is correct
  ✓ No data quality issues

Fail: Returns rows
  ✗ Example output:
    model_name       | event_id  | fetched_at          | current_time        | time_difference
    -----------------|-----------|---------------------|---------------------|----------------
    int_push_events  | 123456... | 2026-07-10 15:00:00 | 2026-07-09 10:00:00 | 1 day 05:00:00
  
  ✗ Action: Investigate why fetched_at is 1 day + 5 hours in the future
*/
