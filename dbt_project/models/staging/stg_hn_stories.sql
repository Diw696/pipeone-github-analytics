/*
================================================================================
MODEL: stg_hn_stories
================================================================================

DESCRIPTION:
  Bronze layer staging model for Hacker News stories. This is a lightweight
  passthrough that reads from the raw ingestion table and standardizes column
  names and types without applying business logic or transformations.

  Mirrors the pattern established by stg_github_events — minimal transformation,
  preserving raw_json for downstream Silver layer parsing.

PURPOSE:
  - Provide a documented, type-safe interface to raw HN stories
  - Convert Unix timestamps to proper TIMESTAMP WITH TIME ZONE
  - Standardize column naming conventions (snake_case)
  - Preserve raw_json JSONB for downstream Silver layer enrichment
  - Serve as the single point of reference for all HN story data

GRAIN:
  One row per Hacker News story (same as source table)

DEPENDENCIES:
  - Source: hn_raw_source.hn_stories_raw (created by HN ingestion pipeline)

DOWNSTREAM MODELS:
  - Silver: int_hn_stories (cleaning, enrichment)
  - Silver: int_hn_repo_mentions (repository mention detection)

MATERIALIZATION:
  View (default) - No storage overhead, always fresh

OWNER: Data Engineering Team
CREATED: Multi-Source Evolution (July 2026)

================================================================================
*/

{{ config(
    materialized='view',
    tags=['staging', 'hackernews', 'bronze']
) }}

/*
--------------------------------------------------------------------------------
CTE: source
--------------------------------------------------------------------------------
Purpose: Read from the raw source table using the source() macro

Uses source() for the same reasons as stg_github_events:
  1. Centralized documentation (table metadata lives in _sources.yml)
  2. Automatic lineage tracking
  3. Freshness monitoring capability
  4. Easy refactoring
--------------------------------------------------------------------------------
*/
with source as (

    select * from {{ source('hn_raw_source', 'hn_stories_raw') }}

),

/*
--------------------------------------------------------------------------------
CTE: renamed
--------------------------------------------------------------------------------
Purpose: Standardize column names and apply explicit type casting

Key transformation:
  - 'time' (Unix timestamp) → 'published_at' (TIMESTAMP WITH TIME ZONE)
  - All other columns passed through with consistent snake_case naming
  - raw_json preserved as-is for downstream Silver layer parsing
--------------------------------------------------------------------------------
*/
renamed as (

    select

        -- Primary Key
        story_id,

        -- Content Attributes
        title,
        author,
        url,

        -- Engagement Metrics (mutable — refreshed on re-ingestion)
        score,
        coalesce(descendants, 0) as comment_count,

        -- Story Classification
        type as story_type,

        -- Temporal Attributes
        -- Convert Unix timestamp to proper PostgreSQL timestamp
        -- The HN API returns 'time' as seconds since epoch (e.g., 1720000000)
        to_timestamp(time) at time zone 'UTC' as published_at,

        -- Pipeline Metadata
        -- fetched_at is when WE ingested the story (our pipeline timestamp)
        -- published_at (above) is when the story was submitted to HN
        fetched_at::timestamp with time zone as fetched_at,

        -- Raw Payload
        -- Preserved as-is for downstream Silver layer enrichment
        raw_json

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
