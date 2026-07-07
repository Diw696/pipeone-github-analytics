/*
================================================================================
MODEL: stg_github_events
================================================================================

DESCRIPTION:
  Bronze layer staging model for GitHub events. This is a lightweight passthrough
  that reads from the raw ingestion table and standardizes column names and types
  without applying business logic or transformations.

PURPOSE:
  - Provide a documented, type-safe interface to raw GitHub events
  - Standardize column naming conventions (snake_case)
  - Preserve raw_payload JSONB for downstream Silver layer parsing
  - Serve as the single point of reference for all GitHub event data

GRAIN:
  One row per GitHub event (same as source table)

DEPENDENCIES:
  - Source: github_raw_source.github_events_raw (created by Week 1 ingestion pipeline)

DOWNSTREAM MODELS:
  - Silver models will parse event-specific fields from raw_payload
  - Gold models will aggregate metrics from Silver models

MATERIALIZATION:
  View (default) - No storage overhead, always fresh

OWNER: Data Engineering Team
CREATED: Week 2 Day 2 (July 2026)

================================================================================
*/

{{ config(
    materialized='view',
    tags=['staging', 'github', 'bronze']
) }}

/*
--------------------------------------------------------------------------------
CTE: source
--------------------------------------------------------------------------------
Purpose: Read from the raw source table using the source() macro

Why use source() instead of hardcoding the table name?
  1. Centralized documentation (table metadata lives in _sources.yml)
  2. Automatic lineage tracking (dbt knows this model depends on the source)
  3. Freshness monitoring (can run dbt source freshness to check data recency)
  4. Easy refactoring (if schema/table changes, update one YAML file)

What dbt compiles this to:
  {{ source('github_raw_source', 'github_events_raw') }}
  
  Becomes:
  pipeone_warehouse.public.github_events_raw
--------------------------------------------------------------------------------
*/
with source as (

    select * from {{ source('github_raw_source', 'github_events_raw') }}

),

/*
--------------------------------------------------------------------------------
CTE: renamed
--------------------------------------------------------------------------------
Purpose: Standardize column names and apply explicit type casting

Why explicit casting?
  - Makes data types visible in the model (self-documenting)
  - Catches type mismatches early (fails at build time, not query time)
  - Ensures consistency across different database engines

Why preserve raw_payload without transformation?
  - Different event types have different nested structures
  - Silver models will parse event-specific fields (PushEvent vs PullRequestEvent)
  - Keeps staging layer lightweight and reusable
  - Maintains flexibility for future event types
--------------------------------------------------------------------------------
*/
renamed as (

    select
        
        -- Primary Key
        event_id,
        
        -- Dimensional Attributes
        repo_name,
        event_type,
        
        -- Temporal Attributes
        -- Note: fetched_at is when WE ingested the event (our pipeline timestamp)
        --       The actual GitHub event timestamp is in raw_payload->>'created_at'
        fetched_at::timestamp with time zone as fetched_at,
        
        -- Raw Payload
        -- Preserved as-is for downstream Silver layer parsing
        -- Structure varies by event_type:
        --   - PushEvent: contains commits array
        --   - PullRequestEvent: contains PR metadata
        --   - IssuesEvent: contains issue details
        raw_payload

    from source

)

/*
--------------------------------------------------------------------------------
Final SELECT
--------------------------------------------------------------------------------
Purpose: Return the cleaned dataset with standardized naming and types

Note: No filtering, no aggregation, no business logic.
This is intentionally a "thin" model that maintains 1:1 grain with the source.
--------------------------------------------------------------------------------
*/
select * from renamed
