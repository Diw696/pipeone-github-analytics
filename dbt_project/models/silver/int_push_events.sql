/*
================================================================================
MODEL: int_push_events
================================================================================

DESCRIPTION:
  Silver layer model that parses PushEvent-specific fields from the Bronze
  staging layer. Flattens JSONB payload into typed, queryable columns.

PURPOSE:
  - Extract push-specific metadata (push_id, ref, commit count)
  - Extract actor information (GitHub username)
  - Provide clean, typed interface for downstream Gold models

GRAIN:
  One row per PushEvent (same as filtered source)

EVENT TYPE:
  PushEvent - Triggered when commits are pushed to a repository branch

UPSTREAM DEPENDENCIES:
  - stg_github_events (Bronze layer)

DOWNSTREAM USAGE:
  - Gold models for commit activity analysis
  - Daily push metrics
  - Contributor activity tracking

MATERIALIZATION:
  View (default) - Lightweight transformation, always fresh

OWNER: Data Engineering Team
CREATED: Week 2 Day 3 (July 2026)

================================================================================
*/

{{ config(
    materialized='view',
    tags=['silver', 'github', 'push_events']
) }}

/*
--------------------------------------------------------------------------------
CTE: base
--------------------------------------------------------------------------------
Purpose: Read from Bronze staging layer using ref() macro

Why ref() instead of hardcoding table name?
  1. Dependency tracking - dbt knows this model depends on stg_github_events
  2. Build ordering - dbt will build stg_github_events first
  3. Automatic lineage - dbt docs shows data flow
  4. Refactoring safety - Rename stg_github_events once, not in 50 models

What dbt compiles this to:
  {{ ref('stg_github_events') }}
  
  Becomes:
  pipeone_warehouse.dbt_dev.stg_github_events
--------------------------------------------------------------------------------
*/
with base as (

    select * from {{ ref('stg_github_events') }}

),

/*
--------------------------------------------------------------------------------
CTE: push_events_only
--------------------------------------------------------------------------------
Purpose: Filter to only PushEvent records

Why filter in a separate CTE?
  - Clear separation of concerns
  - Easy to debug (can query this CTE directly in compiled SQL)
  - Reduces rows early in the transformation (performance)
--------------------------------------------------------------------------------
*/
push_events_only as (

    select * from base
    where event_type = 'PushEvent'

),

/*
--------------------------------------------------------------------------------
CTE: parsed
--------------------------------------------------------------------------------
Purpose: Extract and flatten JSONB fields into typed columns

JSONB Navigation Patterns:
  - raw_payload -> 'key'        Returns JSONB (for chaining)
  - raw_payload ->> 'key'       Returns TEXT (final extraction)
  - raw_payload -> 'a' -> 'b'   Navigate nested objects
  
Defensive SQL Patterns:
  - COALESCE(value, default)    Handle NULL values gracefully
  - ::datatype                   Explicit type casting for safety

Why preserve event_id, repo_name, fetched_at?
  - These are dimensional attributes needed for joins and filtering
  - Inherited from Bronze layer (already clean and typed)
--------------------------------------------------------------------------------
*/
parsed as (

    select
        
        -- Primary Key & Dimensions (inherited from Bronze)
        event_id,
        repo_name,
        fetched_at,
        
        -- Actor Information
        -- Path: raw_payload -> 'actor' -> 'login'
        -- Example: {"actor": {"id": 123, "login": "alice"}} -> "alice"
        raw_payload -> 'actor' ->> 'login' as actor_username,
        
        -- Push Metadata
        -- Path: raw_payload -> 'payload' -> 'push_id'
        -- Example: {"payload": {"push_id": 9876543210}} -> "9876543210"
        -- Note: Stored as TEXT by GitHub, could cast to BIGINT if needed
        raw_payload -> 'payload' ->> 'push_id' as push_id,
        
        -- Git Reference (Branch/Tag)
        -- Path: raw_payload -> 'payload' -> 'ref'
        -- Example: {"payload": {"ref": "refs/heads/main"}} -> "refs/heads/main"
        -- Common values: 'refs/heads/main', 'refs/heads/develop', 'refs/tags/v1.0'
        raw_payload -> 'payload' ->> 'ref' as commit_ref,
        
        -- Commit Count (Defensive SQL)
        -- Path: raw_payload -> 'payload' -> 'commits' (array)
        -- Returns: Number of commits in the push
        --
        -- Defensive Logic:
        --   1. raw_payload -> 'payload' -> 'commits'  (extract commits array as JSONB)
        --   2. jsonb_array_length(...)                (count elements, returns NULL if not array)
        --   3. COALESCE(..., 0)                       (if NULL, return 0)
        --
        -- Why defensive?
        --   - 'commits' key might be missing (API change, malformed event)
        --   - 'commits' might be NULL instead of empty array []
        --   - Without COALESCE, NULL propagates to downstream models
        --
        -- Alternative without COALESCE:
        --   jsonb_array_length(raw_payload -> 'payload' -> 'commits') as commit_count
        --   ^ Would return NULL for missing/invalid data, breaking aggregations like SUM()
        coalesce(
            jsonb_array_length(raw_payload -> 'payload' -> 'commits'),
            0
        ) as commit_count

    from push_events_only

)

/*
--------------------------------------------------------------------------------
Final SELECT
--------------------------------------------------------------------------------
Purpose: Return the parsed dataset with clean, typed columns

What changed from Bronze to Silver?
  Bronze: 1 JSONB column (raw_payload) with nested data
  Silver: 7 typed columns (event_id, repo_name, fetched_at, actor_username,
          push_id, commit_ref, commit_count)

Why Silver models are powerful:
  - No more JSON operators in downstream models
  - Type-safe (commit_count is INTEGER, not TEXT)
  - Fast queries (no JSON parsing at query time if materialized as table)
  - Clear column names (commit_count vs raw_payload->'payload'->>'size')
--------------------------------------------------------------------------------
*/
select * from parsed
