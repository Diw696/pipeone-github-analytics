/*
================================================================================
MODEL: int_hn_stories
================================================================================

DESCRIPTION:
  Silver layer model that cleans, validates, and enriches Hacker News stories
  from the Bronze staging layer. Adds derived fields and filters to actual
  stories only (excluding jobs, polls, and deleted items).

PURPOSE:
  - Filter to valid story records (type = 'story')
  - Extract URL domain for source analysis
  - Add story age calculation
  - Provide clean, typed interface for downstream Gold models

GRAIN:
  One row per valid HN story (filtered from source)

UPSTREAM DEPENDENCIES:
  - stg_hn_stories (Bronze layer)

DOWNSTREAM USAGE:
  - Gold: dim_hn_story (story dimension)
  - Gold: fct_hn_daily_activity (daily aggregation)

MATERIALIZATION:
  View (default) - Lightweight transformation, always fresh

OWNER: Data Engineering Team
CREATED: Multi-Source Evolution (July 2026)

================================================================================
*/

{{ config(
    materialized='view',
    tags=['silver', 'hackernews', 'stories']
) }}

/*
--------------------------------------------------------------------------------
CTE: base
--------------------------------------------------------------------------------
Purpose: Read from Bronze staging layer using ref() macro
--------------------------------------------------------------------------------
*/
with base as (

    select * from {{ ref('stg_hn_stories') }}

),

/*
--------------------------------------------------------------------------------
CTE: stories_only
--------------------------------------------------------------------------------
Purpose: Filter to actual story records

Why filter here?
  - The HN API can return items of type 'job', 'poll', or 'comment'
  - We only want stories for analytics
  - Filtering early reduces downstream processing
--------------------------------------------------------------------------------
*/
stories_only as (

    select * from base
    where story_type = 'story'
      and title is not null

),

/*
--------------------------------------------------------------------------------
CTE: enriched
--------------------------------------------------------------------------------
Purpose: Add derived fields for downstream analytics

Derived fields:
  - url_domain: Extracted hostname from the URL (NULL for text posts)
  - has_url: Boolean flag distinguishing link posts from Ask HN / Show HN
  - activity_date: Date portion of published_at for daily aggregation

URL domain extraction uses regexp_replace to strip protocol and path:
  'https://www.example.com/article/123' → 'www.example.com'
  NULL → NULL (text-only posts like Ask HN)
--------------------------------------------------------------------------------
*/
enriched as (

    select

        -- Primary Key & Content
        story_id,
        title,
        author,
        url,
        score,
        comment_count,
        story_type,
        published_at,
        fetched_at,

        -- Derived: URL domain for source analysis
        -- Extract the hostname from the URL, stripping protocol and path
        case
            when url is not null and url != ''
            then regexp_replace(
                regexp_replace(url, '^https?://', ''),
                '/.*$', ''
            )
            else null
        end as url_domain,

        -- Derived: Boolean flag for link vs text posts
        case
            when url is not null and url != '' then true
            else false
        end as has_url,

        -- Derived: Calendar date for daily aggregation
        -- Uses published_at (when story was submitted), not fetched_at
        published_at::date as activity_date

    from stories_only

)

/*
--------------------------------------------------------------------------------
Final SELECT
--------------------------------------------------------------------------------
Purpose: Return enriched story dataset

Bronze to Silver Transformation:
  Bronze:
    - All item types (story, job, poll)
    - Raw Unix timestamp converted to TIMESTAMPTZ
    - No derived fields

  Silver:
    - Filtered to stories only
    - URL domain extracted
    - Link vs text classification
    - Activity date derived for daily aggregation
--------------------------------------------------------------------------------
*/
select * from enriched
