/*
================================================================================
MODEL: dim_repository
================================================================================
DESCRIPTION:
  Gold layer dimension table containing repository master data.
  One row per repository, with activity metrics denormalized for fast dashboards.

GRAIN:
  One row per unique repository (repo_name)
================================================================================
*/

{{ config(
    materialized='table',
    tags=['gold', 'github', 'dimensions']
) }}

with all_repos as (

    select distinct repo_name
    from {{ ref('int_push_events') }}
    
    union
    
    select distinct repo_name
    from {{ ref('int_pull_requests') }}

),

push_activity as (

    select
        repo_name,
        count(1) as total_pushes,
        coalesce(sum(commit_count), 0) as total_commits,
        min(fetched_at::date) as push_first_seen,
        max(fetched_at::date) as push_last_seen
    from {{ ref('int_push_events') }}
    group by repo_name

),

pr_activity as (

    select
        repo_name,
        count(1) as total_pr_events,
        min(fetched_at::date) as pr_first_seen,
        max(fetched_at::date) as pr_last_seen
    from {{ ref('int_pull_requests') }}
    group by repo_name

),

combined as (

    select
        all_repos.repo_name,
        coalesce(push_activity.total_pushes, 0) as total_pushes,
        coalesce(push_activity.total_commits, 0) as total_commits,
        coalesce(pr_activity.total_pr_events, 0) as total_pr_events,
        coalesce(push_activity.push_first_seen, pr_activity.pr_first_seen) as first_active_date,
        coalesce(push_activity.push_last_seen, pr_activity.pr_last_seen) as last_active_date
    from all_repos
    left join push_activity using (repo_name)
    left join pr_activity using (repo_name)

),

with_surrogate_key as (

    select
        md5(repo_name || '|' || '2026-07-13') as repo_id,
        repo_name,
        total_pushes,
        total_commits,
        total_pr_events,
        first_active_date,
        last_active_date
    from combined

),

with_metadata as (

    select
        repo_id,
        repo_name,
        -- Extract owner from 'owner/repo' format
        split_part(repo_name, '/', 1) as owner,
        -- Hardcoded language (from GitHub repository metadata)
        case repo_name
            when 'facebook/react' then 'JavaScript'
            when 'microsoft/vscode' then 'TypeScript'
            when 'vercel/next.js' then 'JavaScript'
            else 'Unknown'
        end as language,
        -- Hardcoded stars (from GitHub as of Week 3, approximate)
        case repo_name
            when 'facebook/react' then 225000
            when 'microsoft/vscode' then 165000
            when 'vercel/next.js' then 125000
            else 0
        end as stars,
        total_pushes,
        total_commits,
        total_pr_events,
        first_active_date,
        last_active_date
    from with_surrogate_key

),

final as (

    select
        repo_id,
        repo_name,
        owner,
        language,
        stars,
        total_pushes,
        total_commits,
        total_pr_events,
        first_active_date,
        last_active_date,
        current_timestamp at time zone 'UTC' as created_at
    from with_metadata

)

select * from final