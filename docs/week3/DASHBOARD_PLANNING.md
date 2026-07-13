# Phase 6: Dashboard Planning - 5 Scenarios & SQL Templates

## Overview

This document maps each Gold Layer model to specific dashboard visualizations with exact SQL queries and column usage. These are the blueprints for Week 4 dashboard development.

---

## Dashboard Scenario 1: Repository Health Scorecard

**Purpose:** Executive dashboard showing overall health of each monitored repository

**Where to Look:** `dim_repository` (static overview) + latest row from `fct_github_daily_activity`

**Visualizations:**

1. **Repository Overview Cards** (One card per repo)
   - Repo name, owner, language, stars
   - Total pushes (lifetime)
   - Total commits (lifetime)
   - Total PR events (lifetime)

**SQL Template:**
```sql
SELECT 
    repo_name,
    owner,
    language,
    stars,
    total_pushes,
    total_commits,
    total_pr_events,
    last_active_date
FROM dim_repository
ORDER BY total_commits DESC
```

Expected columns: 8
Expected rows: 3 (one per repo)

---

## Dashboard Scenario 2: Daily Activity Trends

**Purpose:** Time-series view showing commit and PR activity over time

**Where to Look:** `fct_github_daily_activity` (grain: repo + date)

**Visualizations:**

1. **Daily Commits Trend** (Line chart)
   - X-axis: Date
   - Y-axis: Commit count
   - Series: One line per repo (facebook/react, microsoft/vscode, vercel/next.js)

2. **Daily PR Events Trend** (Line chart)
   - X-axis: Date
   - Y-axis: PR event count
   - Series: One line per repo

3. **PR Merge Rate by Date** (Line chart or area chart)
   - X-axis: Date
   - Y-axis: pr_merged_pct (percentage merged)
   - Shows code review health over time

**SQL Template:**
```sql
SELECT 
    activity_date,
    repo_name,
    commit_count,
    pr_event_count,
    pr_merged_pct,
    total_activity_count,
    pr_merged
FROM fct_github_daily_activity
WHERE activity_date >= CURRENT_DATE - 90  -- Last 90 days
ORDER BY repo_name, activity_date
```

Expected columns: 7
Expected rows: ~270 (3 repos × 90 days)
Typical query time: <100ms

**Filtering Options:**
- Date range (last 7 days, last 30 days, last 90 days, custom)
- Repository filter (single repo or all)

---

## Dashboard Scenario 3: Contributor Leaderboard with Repo Drill-Down

**Purpose:** Ranking contributors by activity with ability to drill into specific repos

**Where to Look:** `dim_contributor` (static profiles) + `fct_contributor_daily_activity` (activity details)

**Visualizations:**

1. **Top Contributors (Global)** (Table or ranked list)
   - Rank, username, contrib_type, total_commits, total_pr_events
   - Sortable by any column
   - Click to drill: Opens "Contributor Detail" view

2. **Contributor Detail (Drill-Down)** (Table)
   - Shows this contributor's activity per repo
   - Columns: repo_name, days_active, total_pushes, commits_in_pushes, total_pr_events, pr_merged_pct
   - Click repo row to drill further: Shows calendar heatmap for that contributor-repo

**SQL Template - Leaderboard:**
```sql
SELECT 
    username,
    contrib_type,
    total_push_events,
    total_commits,
    total_pr_events,
    first_active_date,
    last_active_date
FROM dim_contributor
ORDER BY total_commits DESC
LIMIT 20  -- Top 20
```

Expected columns: 7
Expected rows: 20 (top contributors)

**SQL Template - Contributor Detail:**
```sql
SELECT 
    repo_name,
    COUNT(*) as days_active,
    SUM(push_count) as total_pushes,
    SUM(commits_in_pushes) as total_commits,
    SUM(pr_event_count) as total_pr_events,
    ROUND(AVG(pr_merged_pct), 2) as avg_pr_merge_rate
FROM fct_contributor_daily_activity
WHERE username = 'alice'  -- Selected contributor
GROUP BY repo_name
ORDER BY total_commits DESC
```

Expected columns: 6
Expected rows: 1-3 (repos this contributor is active in)

---

## Dashboard Scenario 4: Contributor Heat Map

**Purpose:** Visual grid showing contributor activity intensity across repos and time

**Where to Look:** `fct_contributor_daily_activity` (grain: contributor + repo + date)

**Visualization:** Interactive heatmap
- Rows: Contributors (sorted by total activity)
- Columns: Repos
- Cell color intensity: total_activity_count (darker = more active)
- Cell hover: Shows detailed metrics (push_count, pr_event_count, contribution_type)

**SQL Template:**
```sql
SELECT 
    username,
    repo_name,
    SUM(push_count) as total_pushes,
    SUM(commits_in_pushes) as total_commits,
    SUM(pr_event_count) as total_pr_events,
    SUM(total_activity_count) as total_activity,
    AVG(contribution_type) as primary_contribution_type,
    COUNT(DISTINCT activity_date) as days_active
FROM fct_contributor_daily_activity
GROUP BY username, repo_name
ORDER BY total_activity DESC
```

Alternative (if you want time dimension):
```sql
SELECT 
    username,
    repo_name,
    DATE_TRUNC('week', activity_date)::date as week_start,
    SUM(total_activity_count) as weekly_activity
FROM fct_contributor_daily_activity
GROUP BY username, repo_name, week_start
ORDER BY week_start DESC, weekly_activity DESC
```

Expected columns: 7-8
Expected rows: ~300-600 (100-200 contributors × 3 repos)

**Interactivity:**
- Filter by time period (today, last 7 days, last 30 days, all time)
- Filter by repo
- Filter by contribution type (push_only, pr_only, both)
- Hover cell to see detailed metrics

---

## Dashboard Scenario 5: Repository Contribution Breakdown

**Purpose:** Show how each repository's contributions are distributed across contributors

**Where to Look:** `fct_contributor_daily_activity` aggregated by repo and contributor

**Visualizations:**

1. **Contribution Share by Repo** (Stacked bar or pie chart)
   - For each repo, show what % of commits come from top N contributors
   - Bars: Repos (facebook/react, microsoft/vscode, vercel/next.js)
   - Stack segments: Top 5 contributors + "Others"
   - Y-axis: Total commits

2. **Contributor Diversity Metrics** (KPI cards)
   - Repos with high concentration (one person = 50%+): "Bottleneck risk"
   - Repos with low concentration (top 5 = 30%): "Healthy distribution"

**SQL Template - Contribution Share:**
```sql
WITH contributor_totals AS (
    SELECT 
        repo_name,
        username,
        SUM(commits_in_pushes) as total_commits
    FROM fct_contributor_daily_activity
    GROUP BY repo_name, username
),

ranked_contributors AS (
    SELECT 
        repo_name,
        username,
        total_commits,
        ROW_NUMBER() OVER (PARTITION BY repo_name ORDER BY total_commits DESC) as rank
    FROM contributor_totals
)

SELECT 
    repo_name,
    CASE 
        WHEN rank <= 5 THEN username
        ELSE 'Others'
    END as contributor_group,
    SUM(total_commits) as commits
FROM ranked_contributors
GROUP BY repo_name, contributor_group
ORDER BY repo_name, commits DESC
```

Expected columns: 3
Expected rows: ~18 (3 repos × 6 groups: top 5 + others)

**SQL Template - Concentration Metrics:**
```sql
WITH contributor_share AS (
    SELECT 
        repo_name,
        username,
        SUM(commits_in_pushes) as contrib_commits,
        SUM(SUM(commits_in_pushes)) OVER (PARTITION BY repo_name) as repo_total,
        ROUND((SUM(commits_in_pushes)::NUMERIC / SUM(SUM(commits_in_pushes)) OVER (PARTITION BY repo_name)) * 100, 2) as pct_share
    FROM fct_contributor_daily_activity
    GROUP BY repo_name, username
)

SELECT 
    repo_name,
    MAX(pct_share) as top_contributor_pct,
    SUM(CASE WHEN ROW_NUMBER() OVER (PARTITION BY repo_name ORDER BY pct_share DESC) <= 5 THEN pct_share ELSE 0 END) as top_5_pct,
    CASE 
        WHEN MAX(pct_share) > 50 THEN 'High Risk - Bottleneck'
        WHEN MAX(pct_share) > 30 THEN 'Medium Risk'
        ELSE 'Healthy - Distributed'
    END as diversity_assessment
FROM contributor_share
GROUP BY repo_name
```

Expected columns: 4
Expected rows: 3 (one per repo)

---

## SQL Quick Reference Table

| Dashboard | Primary Table | Grain | Query Complexity | Expected Rows |
|-----------|---------------|-------|------------------|---------------|
| Repository Health | dim_repository | Repo | Simple (1 table, no GROUP BY) | 3 |
| Daily Trends | fct_github_daily_activity | (Repo, Date) | Simple (1 table) | 1K-3K |
| Contributor Leaderboard | dim_contributor + fct_contributor_daily_activity | (Contributor, Repo) | Medium (1-2 tables, GROUP BY) | 100-300 |
| Heat Map | fct_contributor_daily_activity | (Contributor, Repo, Date) | Medium (GROUP BY 2-3 cols) | 100K-300K |
| Contribution Breakdown | fct_contributor_daily_activity | (Repo, Contributor) | Complex (window functions) | 18-50 |

---

## Week 4 Dashboard Development Roadmap

**Week 4 Tasks (Next Phase):**
1. Implement Scenario 1 (Repository Health Scorecard) - simplest, builds confidence
2. Implement Scenario 2 (Daily Activity Trends) - core time-series
3. Implement Scenario 3 (Contributor Leaderboard) - introduces JOINs
4. Implement Scenario 4 (Heat Map) - high-cardinality data handling
5. Implement Scenario 5 (Contribution Breakdown) - window functions

**Technology Choice (TBD):**
- **Streamlit**: Python-based, fastest iteration, good for exploratory
- **Power BI**: Enterprise-grade, polished visuals, better for stakeholders
- **Superset**: Open-source, SQL-based, good for data team

Recommend **Streamlit** for Week 4 (quick iteration + Python familiarity), then migrate to Power BI if needed for presentations.

