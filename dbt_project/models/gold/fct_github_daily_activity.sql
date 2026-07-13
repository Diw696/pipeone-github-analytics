/*
================================================================================
MODEL: fct_github_daily_activity
================================================================================
GRAIN: One row per (repository, date) combination[cite: 2]
================================================================================
*/

{{ config(
    materialized='table',
    tags=['gold', 'github', 'facts', 'daily']
) }}

with push_metrics as (

    select
        repo_name,
        fetched_at::date as activity_date,
        count(1) as push_count,
        coalesce(sum(commit_count), 0) as commit_count,
        round(
            coalesce(sum(commit_count), 0)::numeric / 
            nullif(count(1), 0)::numeric,
            2
        ) as push_avg_commits
    from {{ ref('int_push_events') }}
    group by repo_name, fetched_at::date

),

pr_metrics as (

    select
        repo_name,
        fetched_at::date as activity_date,
        count(1) as pr_event_count,
        sum(case when pr_action = 'opened' then 1 else 0 end) as pr_opened,
        sum(case when pr_action in ('closed', 'merged') then 1 else 0 end) as pr_closed,
        sum(case when pr_action = 'merged' then 1 else 0 end) as pr_merged,
        sum(case when pr_action not in ('opened', 'closed', 'merged') then 1 else 0 end) as pr_other_events
    from {{ ref('int_pull_requests') }}
    group by repo_name, fetched_at::date

),

daily_activity as (

    select
        coalesce(push_metrics.repo_name, pr_metrics.repo_name) as repo_name,
        coalesce(push_metrics.activity_date, pr_metrics.activity_date) as activity_date,
        coalesce(push_metrics.push_count, 0) as push_count,
        coalesce(push_metrics.commit_count, 0) as commit_count,
        coalesce(push_metrics.push_avg_commits, 0) as push_avg_commits,
        coalesce(pr_metrics.pr_event_count, 0) as pr_event_count,
        coalesce(pr_metrics.pr_opened, 0) as pr_opened,
        coalesce(pr_metrics.pr_closed, 0) as pr_closed,
        coalesce(pr_metrics.pr_merged, 0) as pr_merged,
        coalesce(pr_metrics.pr_other_events, 0) as pr_other_events
    from push_metrics
    full outer join pr_metrics
        on push_metrics.repo_name = pr_metrics.repo_name
        and push_metrics.activity_date = pr_metrics.activity_date

),

with_repo_key as (

    select
        daily_activity.repo_name,
        daily_activity.activity_date,
        dim_repository.repo_id,
        daily_activity.push_count,
        daily_activity.commit_count,
        daily_activity.push_avg_commits,
        daily_activity.pr_event_count,
        daily_activity.pr_opened,
        daily_activity.pr_closed,
        daily_activity.pr_merged,
        daily_activity.pr_other_events
    from daily_activity
    left join {{ ref('dim_repository') }}
        on daily_activity.repo_name = dim_repository.repo_name

),

with_derived_metrics as (

    select
        repo_id,
        repo_name,
        activity_date,
        push_count,
        commit_count,
        push_avg_commits,
        pr_event_count,
        pr_opened,
        pr_closed,
        pr_merged,
        pr_other_events,
        case
            when pr_event_count = 0 then null
            else round((pr_merged::numeric / pr_event_count::numeric) * 100, 2)
        end as pr_merged_pct,
        push_count + pr_event_count as total_activity_count
    from with_repo_key

),

final as (

    select
        repo_id,
        repo_name,
        activity_date,
        push_count,
        commit_count,
        push_avg_commits,
        pr_event_count,
        pr_opened,
        pr_closed,
        pr_merged,
        pr_other_events,
        pr_merged_pct,
        total_activity_count,
        current_timestamp at time zone 'UTC' as created_at
    from with_derived_metrics
    order by repo_name, activity_date

)

select * from final