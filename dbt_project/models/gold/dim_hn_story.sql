/*
================================================================================
MODEL: dim_hn_story
================================================================================
DESCRIPTION:
  Gold layer dimension table containing Hacker News story master data.
  One row per unique story, with engagement metrics denormalized for
  fast dashboard queries.

  Mirrors the design pattern of dim_repository — a dimension table
  with all-time metrics pre-computed, surrogate key, and audit timestamp.

GRAIN:
  One row per unique story (story_id)
================================================================================
*/

{{ config(
    materialized='table',
    tags=['gold', 'hackernews', 'dimensions']
) }}

with stories as (

    select * from {{ ref('int_hn_stories') }}

),

with_surrogate_key as (

    select
        md5(story_id::text || '|' || '2026-07-18') as hn_story_key,
        story_id,
        title,
        author,
        url,
        url_domain,
        has_url,
        score,
        comment_count,
        story_type,
        published_at,
        activity_date,
        fetched_at

    from stories

),

final as (

    select
        hn_story_key,
        story_id,
        title,
        author,
        url,
        url_domain,
        has_url,
        score,
        comment_count,
        story_type,
        published_at,
        activity_date,
        fetched_at,
        current_timestamp at time zone 'UTC' as created_at

    from with_surrogate_key

)

select * from final
