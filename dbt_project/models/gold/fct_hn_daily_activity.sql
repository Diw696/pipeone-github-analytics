/*
================================================================================
MODEL: fct_hn_daily_activity
================================================================================
DESCRIPTION:
  Gold layer fact table tracking daily Hacker News activity.
  Aggregates story volume, engagement metrics, and author diversity
  per calendar day.

  Mirrors the design pattern of fct_github_daily_activity — daily grain
  with pre-computed metrics ready for dashboard consumption.

GRAIN:
  One row per calendar date
================================================================================
*/

{{ config(
    materialized='table',
    tags=['gold', 'hackernews', 'facts', 'daily']
) }}

with daily_metrics as (

    select
        activity_date,
        count(1) as story_count,
        coalesce(sum(score), 0) as total_score,
        round(coalesce(avg(score), 0)::numeric, 2) as avg_score,
        coalesce(sum(comment_count), 0) as total_comments,
        round(coalesce(avg(comment_count), 0)::numeric, 2) as avg_comments,
        count(distinct author) as unique_authors,
        coalesce(max(score), 0) as top_score,
        -- Percentage of stories that link to an external URL
        -- (vs text-only Ask HN / Show HN posts)
        round(
            (sum(case when has_url then 1 else 0 end)::numeric /
             nullif(count(1), 0)::numeric) * 100,
            2
        ) as stories_with_url_pct

    from {{ ref('int_hn_stories') }}
    where activity_date is not null
    group by activity_date

),

final as (

    select
        activity_date,
        story_count,
        total_score,
        avg_score,
        total_comments,
        avg_comments,
        unique_authors,
        top_score,
        stories_with_url_pct,
        current_timestamp at time zone 'UTC' as created_at

    from daily_metrics
    order by activity_date

)

select * from final
