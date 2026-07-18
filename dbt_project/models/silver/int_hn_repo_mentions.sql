/*
================================================================================
MODEL: int_hn_repo_mentions
================================================================================

DESCRIPTION:
  Silver layer model that detects mentions of PipeOne's tracked GitHub
  repositories in Hacker News story titles.

  This is the cross-source analytics bridge: it connects community
  traction (HN) to the repositories tracked by the GitHub connector.

PURPOSE:
  - Detect repository mentions using robust regex pattern matching
  - Support multiple mentions per story (e.g., "React vs Next.js")
  - Handle common variations (vscode, VS Code, nextjs, next.js, etc.)
  - Provide clean mention events for Gold layer aggregation

GRAIN:
  One row per (story, mentioned_repo) combination.
  A story mentioning both "React" and "Next.js" produces two rows.

UPSTREAM DEPENDENCIES:
  - int_hn_stories (Silver layer — filtered, enriched stories)

DOWNSTREAM USAGE:
  - Gold: fct_hn_repo_mentions (daily mention counts per repo)

MATCHING STRATEGY:
  Uses PostgreSQL regex (~) with word boundary patterns to avoid
  false positives. Each pattern is designed to match common variations
  while avoiding substring matches:

    react     → matches "React", "ReactJS", "react" but NOT "reactive", "reactor"
    vscode    → matches "vscode", "VSCode", "VS Code" but NOT "vscodeext"
    next.js   → matches "next.js", "Next.js", "nextjs", "NextJS"

MATERIALIZATION:
  View (default) - Lightweight transformation, always fresh

OWNER: Data Engineering Team
CREATED: Multi-Source Evolution (July 2026)

================================================================================
*/

{{ config(
    materialized='view',
    tags=['silver', 'hackernews', 'mentions']
) }}

/*
--------------------------------------------------------------------------------
CTE: stories
--------------------------------------------------------------------------------
Purpose: Read cleaned stories from the Silver layer
--------------------------------------------------------------------------------
*/
with stories as (

    select * from {{ ref('int_hn_stories') }}

),

/*
--------------------------------------------------------------------------------
CTE: repo_patterns
--------------------------------------------------------------------------------
Purpose: Define repository matching patterns as a static values list

This CTE uses VALUES to define patterns inline rather than maintaining
a separate seed file. For three repositories this is simpler and more
maintainable. If the tracked repo list grows beyond ~10, consider
migrating to a dbt seed CSV.

Each row defines:
  - repo_name: The canonical repository identifier (matches dim_repository)
  - pattern: PostgreSQL regex pattern for case-insensitive title matching
--------------------------------------------------------------------------------
*/
repo_patterns as (

    select * from (
        values
            -- facebook/react: Match "react" as a standalone word or with "js" suffix
            -- Avoids: "reactive", "reactor", "reaction"
            ('facebook/react',    '(?:^|[\s\-\.,;:!?\(/"''])(?:react(?:\.?js)?)(?:$|[\s\-\.,;:!?\)/"''])'),

            -- microsoft/vscode: Match "vscode", "vs code", "visual studio code"
            ('microsoft/vscode',  '(?:^|[\s\-\.,;:!?\(/"''])(?:vscode|vs\s*code|visual\s+studio\s+code)(?:$|[\s\-\.,;:!?\)/"''])'),

            -- vercel/next.js: Match "next.js", "nextjs", "next js"
            ('vercel/next.js',    '(?:^|[\s\-\.,;:!?\(/"''])(?:next[\.\s]?js)(?:$|[\s\-\.,;:!?\)/"''])')
    ) as t(repo_name, pattern)

),

/*
--------------------------------------------------------------------------------
CTE: mentions
--------------------------------------------------------------------------------
Purpose: Cross-join stories with patterns and filter to matches

Uses CROSS JOIN + WHERE instead of LATERAL UNNEST for clarity.
Each story is tested against all three patterns. Matching rows are kept.
A story matching two patterns produces two output rows (correct behavior
for "React vs Next.js" comparison stories).
--------------------------------------------------------------------------------
*/
mentions as (

    select
        stories.story_id,
        stories.title,
        stories.author,
        stories.url,
        stories.score,
        stories.comment_count,
        stories.published_at,
        stories.activity_date,
        stories.fetched_at,
        repo_patterns.repo_name as mentioned_repo

    from stories
    cross join repo_patterns
    where lower(stories.title) ~ repo_patterns.pattern

)

/*
--------------------------------------------------------------------------------
Final SELECT
--------------------------------------------------------------------------------
Purpose: Return one row per (story, mentioned_repo) match

This model enables Gold-layer aggregation:
  - Daily mention counts per repo
  - Community score per repo (sum of matching story scores)
  - Trending stories mentioning tracked repositories
--------------------------------------------------------------------------------
*/
select * from mentions
