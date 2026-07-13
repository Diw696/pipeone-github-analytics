/*
================================================================================
MODEL: fct_contributor_daily_activity
================================================================================
GRAIN: One row per (contributor, repository, date) combination[cite: 1]
================================================================================
*/

{{ config(
    materialized='table',
    tags=['gold', 'github', 'facts', 'contributor']
) }}

with contributor_push_activity as (

    select
        actor_username as username,
        repo_name,
        fetched_at::date as activity_date,
        count(1) as push_count,
        coalesce(sum(commit_count), 0) as commits_in_pushes
    from {{ ref('int_push_events') }}
    where actor_username is not null
    group by actor_username, repo_name, fetched_at::date

),

contributor_pr_activity as (

    select
        pr_author as username,
        repo_name,
        fetched_at::date as activity_date,
        count(1) as pr_event_count,
        sum(case when pr_action = 'opened' then 1 else 0 end) as pr_opened,
        sum(case when pr_action in ('closed', 'merged') then 1 else 0 end) as pr_closed,
        sum(case when pr_action = 'merged' then 1 else 0 end) as pr_merged,
        sum(case when pr_action not in ('opened', 'closed', 'merged') then 1 else 0 end) as pr_other_events
    from {{ ref('int_pull_requests') }}
    where pr_author is not null
    group by pr_author, repo_name, fetched_at::date

),

contributor_daily_by_repo as (

    select
        coalesce(
            contributor_push_activity.username,
            contributor_pr_activity.username
        ) as username,
        coalesce(
            contributor_push_activity.repo_name,
            contributor_pr_activity.repo_name
        ) as repo_name,
        coalesce(
            contributor_push_activity.activity_date,
            contributor_pr_activity.activity_date
        ) as activity_date,
        coalesce(contributor_push_activity.push_count, 0) as push_count,
        coalesce(contributor_push_activity.commits_in_pushes, 0) as commits_in_pushes,
        coalesce(contributor_pr_activity.pr_event_count, 0) as pr_event_count,
        coalesce(contributor_pr_activity.pr_opened, 0) as pr_opened,
        coalesce(contributor_pr_activity.pr_closed, 0) as pr_closed,
        coalesce(contributor_pr_activity.pr_merged, 0) as pr_merged,
        coalesce(contributor_pr_activity.pr_other_events, 0) as pr_other_events
    from contributor_push_activity
    full outer join contributor_pr_activity
        on contributor_push_activity.username = contributor_pr_activity.username
        and contributor_push_activity.repo_name = contributor_pr_activity.repo_name
        and contributor_push_activity.activity_date = contributor_pr_activity.activity_date

),

with_dimension_keys as (

    select
        dim_contributor.contrib_id,
        dim_repository.repo_id,
        contributor_daily_by_repo.username,
        contributor_daily_by_repo.repo_name,
        contributor_daily_by_repo.activity_date,
        contributor_daily_by_repo.push_count,
        contributor_daily_by_repo.commits_in_pushes,
        contributor_daily_by_repo.pr_event_count,
        contributor_daily_by_repo.pr_opened,
        contributor_daily_by_repo.pr_closed,
        contributor_daily_by_repo.pr_merged,
        contributor_daily_by_repo.pr_other_events
    from contributor_daily_by_repo
    left join {{ ref('dim_contributor') }}
        on contributor_daily_by_repo.username = dim_contributor.username
    left join {{ ref('dim_repository') }}
        on contributor_daily_by_repo.repo_name = dim_repository.repo_name

),

with_derived_metrics as (

    select
        contrib_id,
        repo_id,
        username,
        repo_name,
        activity_date,
        push_count,
        commits_in_pushes,
        pr_event_count,
        pr_opened,
        pr_closed,
        pr_merged,
        pr_other_events,
        push_count + pr_event_count as total_activity_count,
        case
            when pr_event_count = 0 then null
            else round((pr_merged::numeric / pr_event_count::numeric) * 100, 2)
        end as pr_merged_pct,
        case
            when commits_in_pushes > 0 and pr_event_count = 0 then 'push_only'
            when commits_in_pushes = 0 and pr_event_count > 0 then 'pr_only'
            when commits_in_pushes > 0 and pr_event_count > 0 then 'both'
            else 'unknown'
        end as contribution_type
    from with_dimension_keys

),

final as (

    select
        contrib_id,
        repo_id,
        username,
        repo_name,
        activity_date,
        push_count,
        commits_in_pushes,
        pr_event_count,
        pr_opened,
        pr_closed,
        pr_merged,
        pr_other_events,
        total_activity_count,
        pr_merged_pct,
        contribution_type,
        current_timestamp at time zone 'UTC' as created_at
    from with_derived_metrics
    order by username, repo_name, activity_date

)

select * from final