/*
================================================================================
MODEL: fct_hn_repo_mentions
================================================================================
DESCRIPTION:
  Gold layer fact table tracking repository mentions in Hacker News stories.
  This is the cross-source analytics bridge — it connects community traction
  on Hacker News to the GitHub repositories tracked by PipeOne.

  Aggregates mention counts, community scores, and comment volume per
  (mentioned_repo, date) combination.

GRAIN:
  One row per (mentioned_repo, activity_date) combination

BUSINESS VALUE:
  - Which tracked repository has the most community traction?
  - How does HN interest in React/VSCode/Next.js trend over time?
  - What is the total community score (sum of HN upvotes) per repo?
================================================================================
*/

{{ config(
    materialized='table',
    tags=['gold', 'hackernews', 'facts', 'mentions']
) }}

with mention_metrics as (

    select
        mentioned_repo,
        activity_date,
        count(1) as mention_count,
        coalesce(sum(score), 0) as total_score,
        round(coalesce(avg(score), 0)::numeric, 2) as avg_score,
        coalesce(sum(comment_count), 0) as total_comments,
        round(coalesce(avg(comment_count), 0)::numeric, 2) as avg_comments,
        coalesce(max(score), 0) as top_score

    from {{ ref('int_hn_repo_mentions') }}
    where activity_date is not null
    group by mentioned_repo, activity_date

),

final as (

    select
        mentioned_repo,
        activity_date,
        mention_count,
        total_score,
        avg_score,
        total_comments,
        avg_comments,
        top_score,
        current_timestamp at time zone 'UTC' as created_at

    from mention_metrics
    order by mentioned_repo, activity_date

)

select * from final
