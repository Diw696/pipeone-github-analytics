# Technical Design Document: PipeOne

## Metadata

| Field | Value |
|-------|-------|
| **Project** | PipeOne: GitHub Events Ingestion Pipeline |
| **Author** | Diwakar Kaushik |
| **Track** | Foundations of Data Engineering - Segment 2 - H1: APIs to Warehouse |
| **Last Updated** | June 24, 2026 |
| **Week 1 Goal** | Ingest 3 GitHub repos → 1 PostgreSQL raw table |

---

## What I Learned Writing This Document

- **JSONB vs JSON in PostgreSQL:** JSONB stores data in binary format and supports indexing — I initially thought JSON and JSONB were interchangeable but JSONB is always the right choice for a warehouse because you can run `->` and `->>` operators efficiently on it.

- **Idempotency is a pipeline design principle, not just a word:** I used to think "just don't run the script twice." Now I understand that pipelines WILL re-run — the schema has to make re-runs safe by design, not by luck. The `ON CONFLICT DO NOTHING` pattern is how real DEs solve this.

- **Rate limit headers tell you more than the error:** GitHub sends `X-RateLimit-Remaining` and `X-RateLimit-Reset` on every response — you don't have to wait for a 403 to know you're close to the limit. Proactive checking is better engineering than reactive error handling.

- **Docker volumes vs bind mounts:** I initially confused these. Volumes are managed by Docker and persist across container restarts — bind mounts just link to a folder on your machine. For a database, volumes are always correct.

- **The `.env` pattern is a security boundary, not just convenience:** Once a token is in Git history, rotating it is the only fix — removing the file doesn't help because the history still has it. `.gitignore` has to be set up BEFORE the first commit.

---

## Problem Statement

PulseMetrics wants to track open-source repository health by ingesting GitHub event data. Week 1 builds the foundation: a secure, idempotent pipeline that pulls events from 3 target repos and lands them in PostgreSQL.

**Core Requirements:**
1. Extract GitHub event streams (commits, PRs, issues) from target repositories
2. Store raw JSON in PostgreSQL without data loss
3. Handle API rate limits gracefully
4. Prevent duplicate records (idempotency via event IDs)
5. Keep credentials out of version control

---

## Design Scope

**Week 1 Focus:**
- ✅ GitHub API client with auth
- ✅ PostgreSQL raw table (JSONB storage)
- ✅ Idempotency via PRIMARY KEY
- ✅ Rate limit handling
- ✅ Secure `.env` configuration

**Out of Scope:**
- ❌ dbt transformations (Week 2+)
- ❌ Dashboards (Week 4+)
- ❌ Airflow orchestration (Week 3+)

See `docs/roadmap_3rd_year.md` for future architecture.

---

## Target Data Sources

| Repository | Organization | Justification | Expected Volume |
|------------|--------------|---------------|-----------------|
| **react** | facebook | High-activity UI library, diverse event types | ~500 events/day |
| **vscode** | microsoft | Large contributor base, frequent releases | ~800 events/day |
| **next.js** | vercel | TypeScript-heavy, active community | ~600 events/day |

**API Endpoint:** `https://api.github.com/repos/{owner}/{repo}/events`

**Event Types:** PushEvent, PullRequestEvent, IssuesEvent, WatchEvent, ForkEvent, CreateEvent

**Week 3 Extension:** GitHub Contributors API (`/repos/{owner}/{repo}/contributors`) — same auth, same warehouse, proves pipeline generalizes to new endpoints.

---

## Tech Stack

| Tool | Why | What Breaks Without It |
|------|-----|------------------------|
| **Python 3.11+** | Standard for data engineering | No language to run extraction |
| **requests** | Simple HTTP calls | Can't fetch from GitHub API |
| **python-dotenv** | Loads `.env` → environment | Must hardcode tokens (security risk) |
| **psycopg2** | Python ↔ Postgres driver | Can't connect to database |
| **Docker Compose** | One-command Postgres setup | Manual install/config (error-prone) |
| **PostgreSQL 15** | JSONB support + ACID + free | No persistent storage |

### Why Not Alternatives?

| Alternative | Reason Rejected |
|-------------|----------------|
| SQLite | No JSONB support, limited concurrency |
| MongoDB | Schema-less complicates SQL analytics later |
| Snowflake/BigQuery | Cost prohibitive for learning project |

PostgreSQL wins: relational + JSONB flexibility, smooth cloud migration path, dbt-compatible.

---

## Database Schema

**Table:** `public.github_events_raw`

**Purpose:** Store unmodified API responses (Bronze layer)

```sql
CREATE TABLE IF NOT EXISTS public.github_events_raw (
    event_id        VARCHAR(50) PRIMARY KEY,
    repo_name       VARCHAR(255) NOT NULL,
    event_type      VARCHAR(50),
    event_payload   JSONB NOT NULL,
    actor_login     VARCHAR(255),
    created_at      TIMESTAMP,
    inserted_at     TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT valid_repo_name CHECK (repo_name ~ '^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$')
);

CREATE INDEX idx_repo_created ON public.github_events_raw(repo_name, created_at DESC);
CREATE INDEX idx_event_type ON public.github_events_raw(event_type);
```

### Column Rationale

| Column | Type | Why |
|--------|------|-----|
| `event_id` | VARCHAR(50) PK | Enforces idempotency — duplicate inserts are ignored |
| `repo_name` | VARCHAR(255) | Filter/partition key for multi-repo queries |
| `event_type` | VARCHAR(50) | Fast filtering without parsing JSONB |
| `event_payload` | JSONB | Full API response, schema-flexible |
| `actor_login` | VARCHAR(255) | Denormalized for quick user queries |
| `created_at` | TIMESTAMP | Event time from GitHub (time-series) |
| `inserted_at` | TIMESTAMP | Audit trail for ingestion debugging |

### Idempotency Pattern

```sql
INSERT INTO github_events_raw (event_id, repo_name, event_payload, ...)
VALUES ('12345', 'facebook/react', '{"type": "PushEvent"}', ...)
ON CONFLICT (event_id) DO NOTHING;
```

**Result:** Re-running the script safely skips duplicates. No data duplication.

---

## Data Flow

```
1. Script Start
   └─> Load GITHUB_TOKEN from .env via python-dotenv
   └─> Validate token presence (exit if missing)

2. For each target_repo in [facebook/react, microsoft/vscode, vercel/next.js]:
   └─> Check rate limit status
   └─> If remaining < 100: sleep until reset time
   └─> GET /repos/{owner}/{repo}/events?per_page=100&page=1
   └─> Parse JSON response

3. For each event in response:
   └─> Extract: event_id, repo_name, event_type, actor_login, created_at
   └─> INSERT INTO github_events_raw (event_id, ..., event_payload)
       ON CONFLICT (event_id) DO NOTHING

4. If pagination detected (Link header present):
   └─> Repeat request for page=2, page=3, ... until empty response

5. Log summary:
   └─> Total events fetched: X
   └─> New events inserted: Y
   └─> Duplicate events skipped: Z
   └─> Rate limit remaining: N
```

---

## Security & Risk Mitigations

### 1. Token Protection

**Never hardcode credentials:**
```python
# ❌ WRONG
GITHUB_TOKEN = "ghp_xxx..."

# ✅ CORRECT
import os
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    sys.exit("GITHUB_TOKEN not found in environment")
```

**`.gitignore` must include:**
```
.env
*.env
```

**Verify:** `git status` should NOT show `.env` as untracked.

### 2. Rate Limit Handling

GitHub allows 5000 requests/hour (authenticated). Strategy:

**Proactive:** Check before hitting limit
```python
def check_rate_limit(self):
    response = self.session.get("https://api.github.com/rate_limit")
    remaining = response.json()["resources"]["core"]["remaining"]
    reset_time = response.json()["resources"]["core"]["reset"]
    
    if remaining < 100:
        sleep_seconds = reset_time - time.time() + 10
        logger.warning(f"Rate limit low. Sleeping {sleep_seconds}s")
        time.sleep(sleep_seconds)
```

**Reactive:** Retry on 403/429
```python
if response.status_code in [403, 429]:
    retry_after = int(response.headers.get("Retry-After", 60))
    time.sleep(retry_after)
```

**Monitor:** Log `X-RateLimit-Remaining` on every request.

### 3. SQL Injection Prevention

Always use parameterized queries:
```python
# ❌ VULNERABLE
cursor.execute(f"INSERT INTO events VALUES ('{event_id}')")

# ✅ SAFE
cursor.execute("INSERT INTO events VALUES (%s)", (event_id,))
```

### Risk Register

| Risk | Likelihood | Mitigation | Status |
|------|------------|------------|--------|
| Token leaked in Git | Medium | `.gitignore` + `.env` pattern | ✅ Done |
| Rate limit exceeded | High | Proactive check + backoff | ✅ Done |
| Duplicate ingestion | Medium | PRIMARY KEY constraint | ✅ Done |

---

## Setup Instructions

**Prerequisites:** Docker, Python 3.11+, Git, GitHub PAT

```bash
# Clone and setup
git clone https://github.com/Diw696/pipeone-github-analytics.git
cd pipeone-github-analytics
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure secrets
cp .env.example .env
# Edit .env: add GITHUB_TOKEN=your_token_here

# Start database
docker-compose up -d

# Initialize schema
python scripts/init_db.py

# Run ingestion
python src/ingestion/github_client.py
```

**Docker Compose** (`docker-compose.yml`):
```yaml
version: '3.9'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: pipeone_warehouse
      POSTGRES_USER: pipeone_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pipeone_user"]
      interval: 10s

volumes:
  postgres_data:
```

---

## Testing & Validation

**Test 1: Authentication**
```bash
python -c "from src.ingestion.github_client import GitHubClient; \
           client = GitHubClient(); print(client.check_rate_limit())"
# Expected: JSON showing remaining > 0
```

**Test 2: Idempotency**
```sql
-- Run script twice, then:
SELECT event_id, COUNT(*) 
FROM github_events_raw 
GROUP BY event_id 
HAVING COUNT(*) > 1;
-- Expected: 0 rows (no duplicates)
```

**Test 3: Data Quality**
```sql
SELECT COUNT(*) FROM github_events_raw WHERE event_id IS NULL;       -- Expected: 0
SELECT COUNT(*) FROM github_events_raw WHERE event_payload IS NULL;  -- Expected: 0
SELECT COUNT(*) FROM github_events_raw WHERE repo_name NOT LIKE '%/%';  -- Expected: 0
```

---

## Week 1 Success Criteria

- [ ] GitHub API client authenticates successfully
- [ ] Events ingested from all 3 repos (react, vscode, next.js)
- [ ] Zero duplicate events (verified via SQL query)
- [ ] Rate limit handling prevents 403 errors
- [ ] No credentials committed to Git (`.env` in `.gitignore`)
- [ ] README instructions work on fresh machine

---

## Future Work

See `docs/roadmap_3rd_year.md` for:
- Week 2+: dbt transformations (Silver/Gold layers)
- Week 4+: Streamlit dashboards
- Year 2+: Airflow orchestration, incremental processing, cloud deployment

---

## References

- [GitHub Events API](https://docs.github.com/en/rest/activity/events)
- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html)
- [Docker Compose](https://docs.docker.com/compose/)
- [Rate Limit Best Practices](https://docs.github.com/en/rest/guides/best-practices-for-integrators#dealing-with-rate-limits)

---

**Document End** | Week 1 Focus: Raw Ingestion Only
