/*
================================================================================
MODEL: int_pull_requests
================================================================================

DESCRIPTION:
  Silver layer model that parses PullRequestEvent-specific fields from the
  Bronze staging layer. Flattens JSONB payload into typed, queryable columns.

PURPOSE:
  - Extract pull request metadata (PR ID, title, action)
  - Extract author information
  - Provide clean, typed interface for PR analytics

GRAIN:
  One row per PullRequestEvent (same as filtered source)

EVENT TYPE:
  PullRequestEvent - Triggered when a pull request is opened, closed, merged,
  reopened, synchronized, assigned, unassigned, labeled, unlabeled, etc.

UPSTREAM DEPENDENCIES:
  - stg_github_events (Bronze layer)

DOWNSTREAM USAGE:
  - Gold models for PR lifecycle analysis
  - Code review metrics
  - PR velocity tracking

MATERIALIZATION:
  View (default) - Lightweight transformation, always fresh

OWNER: Data Engineering Team
CREATED: Week 2 Day 3 (July 2026)

================================================================================
*/

{{ config(
    materialized='view',
    tags=['silver', 'github', 'pull_requests']
) }}

/*
--------------------------------------------------------------------------------
CTE: base
--------------------------------------------------------------------------------
Purpose: Read from Bronze staging layer using ref() macro

ref() Benefits:
  - dbt builds stg_github_events before this model
  - dbt docs show lineage: stg_github_events → int_pull_requests
  - Rename stg_github_events once, updates everywhere
  - `dbt run --models +int_pull_requests` runs dependencies automatically
--------------------------------------------------------------------------------
*/
with base as (

    select * from {{ ref('stg_github_events') }}

),

/*
--------------------------------------------------------------------------------
CTE: pull_request_events_only
--------------------------------------------------------------------------------
Purpose: Filter to only PullRequestEvent records

PullRequestEvent vs PullRequestReviewEvent:
  - PullRequestEvent: PR opened, closed, merged, synchronized
  - PullRequestReviewEvent: Review submitted, edited, dismissed
  - We're filtering for PullRequestEvent only

Performance note:
  Filtering here reduces rows before expensive JSONB parsing
--------------------------------------------------------------------------------
*/
pull_request_events_only as (

    select * from base
    where event_type = 'PullRequestEvent'

),

/*
--------------------------------------------------------------------------------
CTE: parsed
--------------------------------------------------------------------------------
Purpose: Extract and flatten JSONB fields into typed columns

PullRequestEvent Payload Structure:
  {
    "type": "PullRequestEvent",
    "payload": {
      "action": "opened",  // or "closed", "merged", "reopened", etc.
      "number": 12345,     // PR number
      "pull_request": {
        "id": 98765432,
        "title": "Fix bug in authentication",
        "state": "open",
        "user": {
          "login": "alice",
          "id": 123
        }
      }
    }
  }

JSONB Navigation:
  - 1 level deep:  raw_payload -> 'payload' ->> 'action'
  - 2 levels deep: raw_payload -> 'payload' -> 'pull_request' ->> 'id'
  - 3 levels deep: raw_payload -> 'payload' -> 'pull_request' -> 'user' ->> 'login'

Operator choice:
  - Use -> until the last step (preserves JSONB for chaining)
  - Use ->> on the final key (extracts as TEXT)
--------------------------------------------------------------------------------
*/
parsed as (

    select
        
        -- Primary Key & Dimensions (inherited from Bronze)
        event_id,
        repo_name,
        fetched_at,
        
        -- Pull Request Action
        -- Path: raw_payload -> 'payload' -> 'action'
        -- Example: {"payload": {"action": "opened"}} -> "opened"
        -- Possible values: 
        --   - "opened" (new PR)
        --   - "closed" (PR closed without merge)
        --   - "reopened" (closed PR reopened)
        --   - "synchronize" (new commits pushed)
        --   - "assigned", "unassigned", "labeled", "unlabeled", etc.
        raw_payload -> 'payload' ->> 'action' as pr_action,
        
        -- Pull Request ID (GitHub's internal ID)
        -- Path: raw_payload -> 'payload' -> 'pull_request' -> 'id'
        -- Example: {"pull_request": {"id": 98765432}} -> "98765432"
        -- Note: This is different from PR number
        --   - PR ID: Global unique identifier (98765432)
        --   - PR number: Repo-specific sequence (#123)
        -- We extract ID here because it's guaranteed unique across all repos
        raw_payload -> 'payload' -> 'pull_request' ->> 'id' as pull_request_id,
        
        -- Pull Request Title
        -- Path: raw_payload -> 'payload' -> 'pull_request' -> 'title'
        -- Example: {"pull_request": {"title": "Fix bug in auth"}} -> "Fix bug in auth"
        -- Note: Titles can contain special characters, emojis, etc.
        -- Stored as TEXT, no additional cleaning needed
        raw_payload -> 'payload' -> 'pull_request' ->> 'title' as pr_title,
        
        -- Pull Request Author
        -- Path: raw_payload -> 'payload' -> 'pull_request' -> 'user' -> 'login'
        -- Example: {"pull_request": {"user": {"login": "alice"}}} -> "alice"
        -- This is the GitHub username of the person who opened the PR
        -- Note: This is NOT the same as the 'actor' in the event
        --   - pr_author: Who created the PR
        --   - actor (not extracted here): Who triggered this specific event
        --     (could be different if someone else closed/merged the PR)
        raw_payload -> 'payload' -> 'pull_request' -> 'user' ->> 'login' as pr_author

    from pull_request_events_only

)

/*
--------------------------------------------------------------------------------
Final SELECT
--------------------------------------------------------------------------------
Purpose: Return the parsed dataset with clean, typed columns

Bronze to Silver Transformation:
  Bronze:
    - 1 row per event (all types mixed)
    - raw_payload JSONB with deeply nested structure
  
  Silver:
    - 1 row per PullRequestEvent (filtered)
    - 7 flat columns: event_id, repo_name, fetched_at, pr_action,
      pull_request_id, pr_title, pr_author

Why this matters:
  - Analysts can query: SELECT repo_name, pr_action, COUNT(*) GROUP BY 1, 2
  - No need to understand JSONB operators
  - Clear column names (pr_action vs raw_payload->'payload'->>'action')
  - Type-safe for downstream joins and aggregations

Example downstream query (Gold layer):
  SELECT 
      repo_name,
      pr_action,
      COUNT(*) as pr_count
  FROM dbt_dev.int_pull_requests
  GROUP BY 1, 2
  
  Result:
    repo_name        | pr_action | pr_count
    -----------------|-----------|---------
    facebook/react   | opened    | 45
    facebook/react   | closed    | 42
    microsoft/vscode | opened    | 38
--------------------------------------------------------------------------------
*/
select * from parsed
