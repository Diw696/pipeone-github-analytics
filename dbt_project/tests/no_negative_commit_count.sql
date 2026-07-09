/*
================================================================================
SINGULAR TEST: no_negative_commit_count
================================================================================

PURPOSE:
  Validate that commit_count is never negative.
  
BUSINESS RULE:
  It is logically impossible to have a negative number of commits.
  commit_count represents array length, which is always >= 0.
  
WHY THIS MATTERS:
  - Negative commit counts break SUM() aggregations
  - Indicates data corruption or parsing errors
  - Could indicate JSONB extraction logic is broken
  - Dashboards show nonsensical metrics

EXPECTED RESULT:
  This query should return 0 rows (test passes).
  If it returns rows, those records have invalid negative commit counts.

FAILURE IMPACT:
  - Daily commit totals are incorrect (undercount)
  - Average commits per push is misleading
  - Repository comparison charts show wrong data
  - Alerts trigger false positives ("Commits dropped 50%!")

REMEDIATION:
  If this test fails:
    1. Check JSONB extraction: jsonb_array_length() logic
    2. Check COALESCE: Should default to 0, not negative
    3. Check type casting: Is commit_count being cast correctly?
    4. Investigate raw_payload: Is GitHub API returning negative values?
    5. Check affected records: SELECT * FROM results of this query

OWNER: Data Engineering Team
CREATED: Week 2 Day 4 (July 2026)

================================================================================
*/

-- Find all records where commit_count is negative
-- This should return 0 rows (if any rows, test fails)

select
    event_id,
    repo_name,
    actor_username,
    commit_count,
    fetched_at
from {{ ref('int_push_events') }}
where commit_count < 0

/*
QUERY EXPLANATION:

1. SELECT clause includes:
   - event_id: Identifier for the bad record
   - repo_name: Which repository has the issue
   - actor_username: Who triggered the push (for debugging)
   - commit_count: The invalid negative value
   - fetched_at: When the bad data was ingested

2. WHERE clause:
   commit_count < 0
   - Finds records with negative commit counts
   - Uses < 0 (not <= 0) because 0 commits is valid (empty push, tags)

3. Why this can happen:
   - Type casting error: TEXT '-5' cast to INTEGER
   - JSONB extraction error: Wrong field accessed
   - Data corruption: Database issue
   - API bug: GitHub returns malformed data

VALID COMMIT COUNT RANGES:

✓ commit_count = 0
  - Valid: Empty push (e.g., tag creation, branch deletion)
  - Valid: Force push with no new commits

✓ commit_count = 1 to 50
  - Typical: Most pushes contain 1-5 commits
  - Normal: Feature branch merge (10-50 commits)

✓ commit_count > 50
  - Rare but valid: Large refactor, vendor code import
  - GitHub API returns up to ~100 commits per event

✗ commit_count < 0
  - Invalid: Logically impossible
  - Indicates data quality issue

TEST SCENARIOS:

Pass: Returns 0 rows
  ✓ All commit_count values are >= 0
  ✓ JSONB extraction is working correctly
  ✓ COALESCE defensive SQL is functioning
  ✓ No data corruption

Fail: Returns rows
  ✗ Example output:
    event_id  | repo_name        | actor_username | commit_count | fetched_at
    ----------|------------------|----------------|--------------|-------------------
    345678... | facebook/react   | alice          | -3           | 2026-07-09 10:00:00
  
  ✗ Action: commit_count is -3, which is impossible!
            Check int_push_events.sql JSONB extraction logic:
            
            Current logic:
            coalesce(
                jsonb_array_length(raw_payload -> 'payload' -> 'commits'),
                0
            ) as commit_count
            
            Potential issues:
            - Is jsonb_array_length returning negative? (shouldn't)
            - Is COALESCE being bypassed somehow?
            - Check raw_payload for this event_id

DEFENSIVE SQL VERIFICATION:

This test validates that our defensive SQL is working:

-- Without COALESCE (could return NULL)
jsonb_array_length(raw_payload -> 'payload' -> 'commits')

-- With COALESCE (defaults to 0)
coalesce(
    jsonb_array_length(raw_payload -> 'payload' -> 'commits'),
    0
)

If this test fails, it means:
  1. Either COALESCE isn't working, OR
  2. jsonb_array_length is returning negative (API bug), OR
  3. commit_count was manually overwritten with bad data
*/
