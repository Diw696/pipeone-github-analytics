/*
================================================================================
MODEL: dim_contributor
================================================================================

DESCRIPTION:
  Gold layer dimension table containing contributor master data.
  One row per unique contributor (GitHub username), with activity metrics
  and contributor classification (push_only, pr_only, or both).

GRAIN:
  One row per unique contributor (username)

PURPOSE:
  - Single source of truth for contributors
  - Classify contributor types (exclusive pushers, exclusive reviewers, hybrid)
  - Enable contributor leaderboards and heat maps
  - Support contributor-level drill-down analytics

*/

{{ config(
    materialized='table',
    tags=['gold', 'github', 'dimensions'],
    unique_id='contrib_id'
) }}


with push_contributors as (

    select
        actor_username,
        count(1) as total_push_events,
        coalesce(sum(commit_count), 0) as total_commits,
        min(fetched_at::date) as push_first_seen,
        max(fetched_at::date) as push_last_seen
    from {{ ref('int_push_events') }}
    where actor_username is not null
    group by actor_username

),


pr_contributors as (

    select
        pr_author,
        count(1) as total_pr_events,
        min(fetched_at::date) as pr_first_seen,
        max(fetched_at::date) as pr_last_seen
    from {{ ref('int_pull_requests') }}
    where pr_author is not null
    group by pr_author

),


all_contributors as (

    select
        coalesce(push_contributors.actor_username, pr_contributors.pr_author) as username,
        coalesce(push_contributors.total_push_events, 0) as total_push_events,
        coalesce(push_contributors.total_commits, 0) as total_commits,
        coalesce(pr_contributors.total_pr_events, 0) as total_pr_events,
        coalesce(push_contributors.push_first_seen, pr_contributors.pr_first_seen) as first_active_date,
        coalesce(push_contributors.push_last_seen, pr_contributors.pr_last_seen) as last_active_date
    from push_contributors
    full outer join pr_contributors
        on push_contributors.actor_username = pr_contributors.pr_author

),


with_contributor_type as (

    select
        username,
        total_push_events,
        total_commits,
        total_pr_events,
        first_active_date,
        last_active_date,
        case
            when total_commits > 0 and total_pr_events = 0
                then 'push_only'
            when total_commits = 0 and total_pr_events > 0
                then 'pr_only'
            when total_commits > 0 and total_pr_events > 0
                then 'both'
            else 'unknown'
        end as contrib_type
    from all_contributors

),


with_surrogate_key as (

    select
        md5(username || '|' || '2026-07-13') as contrib_id,
        username,
        total_push_events,
        total_commits,
        total_pr_events,
        contrib_type,
        first_active_date,
        last_active_date
    from with_contributor_type

),


final as (

    select
        contrib_id,
        username,
        total_push_events,
        total_commits,
        total_pr_events,
        contrib_type,
        first_active_date,
        last_active_date,
        current_timestamp at time zone 'UTC' as created_at
    from with_surrogate_key

)

/*
--------------------------------------------------------------------------------
Final SELECT
--------------------------------------------------------------------------------
Return the complete contributor dimension table
--------------------------------------------------------------------------------
*/
select * from final
