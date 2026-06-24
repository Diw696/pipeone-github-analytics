# Technical Design Document: PipeOne

## Metadata

| Field | Value |
|-------|-------|
| **Project** | PipeOne: GitHub DevActivity Analytics Pipeline |
| **Author** | Diwakar Kaushik |
| **Organization** | PulseMetrics Startup / Lovely Professional University |
| **Track** | Foundations of Data Engineering - Segment 2 - H1: APIs to Warehouse |
| **Status** | ⏳ Awaiting Architecture Sign-Off |
| **Version** | 1.0 |
| **Last Updated** | June 24, 2026 |
| **Review Deadline** | June 27, 2026 (End of Week 1) |

---

## What I Learned Writing This Document

- **JSONB vs JSON in PostgreSQL:** JSONB stores data in binary format and supports indexing — I initially thought JSON and JSONB were interchangeable but JSONB is always the right choice for a warehouse because you can run `->` and `->>` operators efficiently on it.

- **Idempotency is a pipeline design principle, not just a word:** I used to think "just don't run the script twice." Now I understand that pipelines WILL re-run — the schema has to make re-runs safe by design, not by luck. The `ON CONFLICT DO NOTHING` pattern is how real DEs solve this.

- **Rate limit headers tell you more than the error:** GitHub sends `X-RateLimit-Remaining` and `X-RateLimit-Reset` on every response — you don't have to wait for a 403 to know you're close to the limit. Proactive checking is better engineering than reactive error handling.

- **Docker volumes vs bind mounts:** I initially confused these. Volumes are managed by Docker and persist across container restarts — bind mounts just link to a folder on your machine. For a database, volumes are always correct.

- **The `.env` pattern is a security boundary, not just convenience:** Once a token is in Git history, rotating it is the only fix — removing the file doesn't help because the history still has it. `.gitignore` has to be set up BEFORE the first commit.

---

## Problem Statement

### Business Context

PulseMetrics is building a data infrastructure to provide SMBs and tech organizations with actionable intelligence on open-source repository health. Current market solutions lack:

- **Real-time visibility** into developer activity patterns
- **Consolidated views** across multiple high-traffic repositories
- **Historical trend analysis** for commit velocity and PR throughput
- **Cost-effective alternatives** to expensive analytics platforms

### Technical Challenge

We need a **secure, idempotent ingestion infrastructure** that:

1. Extracts public GitHub event streams (commits, PRs, issues, stars) from target repositories
2. Lands raw JSON payloads into a persistent data warehouse without data loss
3. Handles API rate limits gracefully to prevent pipeline disruptions
4. Ensures no duplicate records through event ID tracking (idempotency)
5. Protects sensitive API credentials from exposure in version control

### Success Criteria (Week 1)

- [ ] Successfully ingest events from 3 target repositories
- [ ] Store raw JSON in PostgreSQL with `JSONB` datatype
- [ ] Demonstrate zero data loss during ingestion runs
- [ ] Prevent duplicate event processing via primary key constraints
- [ ] Handle GitHub API rate limits without pipeline failure
- [ ] Pass security audit (no credentials in Git history)

---

## Design Scope

### In Scope (Week 1 Focus)

This design document covers **Phase 1: Raw Data Ingestion Infrastructure** only:

✅ **API Client Development**
- GitHub Events API authentication with Personal Access Token (PAT)
- HTTP request handling with timeout and retry logic
- Rate limit detection using `X-RateLimit-*` response headers
- Pagination support for multi-page event retrieval

✅ **Data Storage Layer**
- PostgreSQL 15 warehouse with Docker Compose orchestration
- Bronze-tier raw table schema with JSONB storage
- Primary key constraint on `event_id` for idempotency
- Timestamp tracking for ingestion auditing

✅ **Security & Configuration**
- Environment variable management via `.env` files
- Git ignore patterns to prevent credential leakage
- Secrets isolation from application code

### Explicitly Out of Scope (Future Phases)

❌ **Data Transformations** (Week 2+)
- dbt staging models (Silver layer)
- Event type parsing and normalization
- Dimensional modeling (star/snowflake schemas)

❌ **Analytics & Visualization** (Week 4+)
- Streamlit dashboard development
- KPI calculations and aggregations
- Real-time update mechanisms

❌ **Orchestration** (Week 3+)
- Apache Airflow DAG scheduling
- Automated backfill jobs
- Dependency management between tasks

❌ **Advanced Features** (Year 2+)
- Incremental processing strategies
- Change Data Capture (CDC)
- Multi-source integration (GitLab, Bitbucket)

---

## Target Data Sources

### Primary Data Sources (Week 1)

| Repository | Organization | Justification | Expected Event Volume |
|------------|--------------|---------------|----------------------|
| **react** | facebook | High-activity UI library, diverse event types | ~500 events/day |
| **vscode** | microsoft | Large contributor base, frequent releases | ~800 events/day |
| **next.js** | vercel | High-activity modern web framework, TypeScript-heavy, diverse contributor base | ~600 events/day |

**Selection Criteria:**
- Public repositories with high commit frequency
- Diverse technology stacks (JavaScript, TypeScript, PHP-adjacent)
- Active maintainer teams (multiple events per hour during business hours)
- Sufficient data volume for meaningful analysis without overwhelming Week 1 infrastructure

### API Endpoints

**GitHub Events API:** `https://api.github.com/repos/{owner}/{repo}/events`

**Event Types Captured:**
- `PushEvent` - Code commits to branches
- `PullRequestEvent` - PR opened/closed/merged
- `IssuesEvent` - Issue creation/updates
- `WatchEvent` - Repository stars
- `ForkEvent` - Repository forks
- `CreateEvent` - Branch/tag creation

### Future Data Source (Week 3 Extension — Mini-Extension)

**GitHub Contributors API:** `https://api.github.com/repos/{owner}/{repo}/contributors`

- **Purpose:** Pull contributor stats (total commits, additions, deletions) for the same 3 repos
- **Use Case:** Combine with events data to build a developer activity leaderboard — who is driving activity in each repo
- **Why this extension:** Same API, same auth token, same warehouse — proves the pipeline generalises to a new endpoint without rebuilding anything
- **Integration:** New raw table `github_contributors_raw`, new dbt models `stg_contributors` + `fct_contributor_leaderboard`

---

## Tech Stack Selection

### Core Technologies

| Technology | Version | Role | Why Chosen | What Breaks If Removed |
|------------|---------|------|------------|------------------------|
| **Python** | 3.11+ | Orchestration & API client | Industry standard for data engineering; rich ecosystem (`requests`, `sqlalchemy`, `pandas`) | No programming language to execute extraction logic |
| **requests** | 2.31.0 | HTTP client library | Simple API for REST calls; handles sessions, retries, timeouts elegantly | Cannot make HTTP requests to GitHub API |
| **python-dotenv** | 1.0.0 | Environment variable loader | Loads `.env` files into `os.environ`; prevents hardcoded secrets | Must hardcode tokens (security breach) |
| **psycopg2-binary** | 2.9.9 | PostgreSQL adapter | Native Python-Postgres driver; supports JSONB operations | Cannot connect to PostgreSQL from Python |
| **Docker Compose** | 2.x | Container orchestration | Single-command Postgres setup; reproducible environments across machines | Must manually install/configure Postgres (error-prone) |
| **PostgreSQL** | 15-alpine | Relational warehouse | JSONB support for semi-structured data; ACID compliance; free and open-source | No persistent storage for ingested data |

### Alternative Approaches Considered

**❌ SQLite:**
- **Rejected:** No native JSONB support; limited concurrency; not production-scalable

**❌ MongoDB:**
- **Rejected:** Schema-less design complicates future SQL-based analytics; overkill for structured events

**❌ Cloud Warehouses (Snowflake/BigQuery):**
- **Rejected:** Cost prohibitive for learning project; local-first approach for Week 1

**✅ PostgreSQL Selected:**
- Best of both worlds: relational structure + JSONB flexibility
- Smooth migration path to cloud-managed Postgres (AWS RDS, GCP Cloud SQL)
- dbt compatibility for future transformation layer

---

## Data Tier Schema

### Bronze Layer: Raw Data Storage

**Table:** `public.github_events_raw`

**Purpose:** Persist unmodified API responses for downstream processing and auditing

#### Schema Definition

```sql
CREATE TABLE IF NOT EXISTS public.github_events_raw (
    event_id        VARCHAR(50) PRIMARY KEY,       -- GitHub event ID (ensures idempotency)
    repo_name       VARCHAR(255) NOT NULL,         -- Format: "owner/repo" (e.g., "facebook/react")
    event_type      VARCHAR(50),                   -- Event type (PushEvent, PullRequestEvent, etc.)
    event_payload   JSONB NOT NULL,                -- Full API response as JSON
    actor_login     VARCHAR(255),                  -- GitHub username who triggered event
    created_at      TIMESTAMP,                     -- Event timestamp from GitHub API
    inserted_at     TIMESTAMP DEFAULT NOW(),       -- Ingestion timestamp (audit trail)
    
    CONSTRAINT valid_repo_name CHECK (repo_name ~ '^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$')
);

-- Index for query performance
CREATE INDEX idx_repo_created ON public.github_events_raw(repo_name, created_at DESC);
CREATE INDEX idx_event_type ON public.github_events_raw(event_type);
CREATE INDEX idx_inserted_at ON public.github_events_raw(inserted_at);
```

#### Column Rationale

| Column | Datatype | Purpose |
|--------|----------|---------|
| `event_id` | VARCHAR(50) PRIMARY KEY | Enforces idempotency; prevents duplicate ingestion if script re-runs |
| `repo_name` | VARCHAR(255) NOT NULL | Partition key for multi-repo queries; enforces naming convention via CHECK constraint |
| `event_type` | VARCHAR(50) | Enables filtering by event category without parsing JSONB |
| `event_payload` | JSONB NOT NULL | Stores full API response; allows schema evolution without ALTER TABLE |
| `actor_login` | VARCHAR(255) | Denormalized for quick user-based queries |
| `created_at` | TIMESTAMP | Event time from GitHub (UTC); used for time-series analysis |
| `inserted_at` | TIMESTAMP DEFAULT NOW() | Audit trail for data freshness tracking and debugging ingestion delays |

#### Idempotency Guarantee

**Problem:** Script may run multiple times due to retries, manual re-execution, or scheduler overlaps.

**Solution:** `event_id` as PRIMARY KEY ensures:
```sql
INSERT INTO github_events_raw (event_id, repo_name, event_payload, ...)
VALUES ('12345', 'facebook/react', '{"type": "PushEvent"}', ...)
ON CONFLICT (event_id) DO NOTHING;
```

Result: Duplicate events are silently ignored; no data duplication.

---

## System Architecture

### Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                     EXTERNAL LAYER                           │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  GitHub Events API                                     │  │
│  │  https://api.github.com/repos/{owner}/{repo}/events   │  │
│  │  Rate Limit: 5000 req/hour (authenticated)            │  │
│  └────────────────┬───────────────────────────────────────┘  │
└────────────────────┼──────────────────────────────────────────┘
                     │ HTTPS GET
                     │ Authorization: token ghp_xxxxx
                     ▼
┌──────────────────────────────────────────────────────────────┐
│                  APPLICATION LAYER (Python)                  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  src/ingestion/github_client.py                        │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │ GitHubClient Class                               │  │  │
│  │  │ • load_dotenv() → GITHUB_TOKEN from .env        │  │  │
│  │  │ • requests.Session() with auth headers          │  │  │
│  │  │ • get_public_events(repo, page=1)               │  │  │
│  │  │ • check_rate_limit() → X-RateLimit headers      │  │  │
│  │  │ • exponential_backoff() on 429 responses        │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  └────────────────┬───────────────────────────────────────┘  │
└────────────────────┼──────────────────────────────────────────┘
                     │ psycopg2 INSERT
                     │ INSERT INTO github_events_raw ...
                     │ ON CONFLICT (event_id) DO NOTHING
                     ▼
┌──────────────────────────────────────────────────────────────┐
│                   DATA LAYER (PostgreSQL)                    │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Docker Container: postgres:15-alpine                  │  │
│  │  Port: 5432 (mapped to host)                           │  │
│  │  Database: pipeone_warehouse                           │  │
│  │  Schema: public.github_events_raw                      │  │
│  │  Storage: Docker volume (persistent across restarts)   │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Data Flow Sequence

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

## System Security & Risk Mitigations

### Security Strategy

#### 1. API Token Protection

**Threat:** Hardcoded credentials exposed in Git history

**Mitigation:**
```python
# ❌ NEVER DO THIS
GITHUB_TOKEN = "ghp_MOCK_TOKEN_VAL_DO_NOT_HARDCODE"

# ✅ CORRECT APPROACH
import os
from dotenv import load_dotenv

load_dotenv()  # Loads .env file
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    logger.error("GITHUB_TOKEN not found in environment")
    sys.exit(1)
```

**`.gitignore` Configuration:**
```
# Critical: Prevent .env from being committed
.env
*.env
.env.local
```

**Verification:** Run `git status` → `.env` should NOT appear in untracked files

#### 2. Rate Limit Handling

**Threat:** GitHub API returns 403 Forbidden when rate limit exceeded → pipeline fails

**Mitigation Strategy:**

**Step 1: Proactive Rate Limit Checking**
```python
def check_rate_limit(self):
    response = self.session.get("https://api.github.com/rate_limit")
    data = response.json()
    
    core_limit = data["resources"]["core"]
    remaining = int(core_limit["remaining"])
    reset_time = int(core_limit["reset"])
    
    if remaining < 100:  # Buffer threshold
        sleep_seconds = reset_time - time.time()
        logger.warning(f"Rate limit low ({remaining}). Sleeping {sleep_seconds}s")
        time.sleep(sleep_seconds + 10)  # +10s buffer
```

**Step 2: Reactive Backoff on 429 Response**
```python
def get_events_with_retry(self, url, max_retries=3):
    for attempt in range(max_retries):
        response = self.session.get(url)
        
        if response.status_code == 200:
            return response.json()
        
        elif response.status_code == 403:  # Rate limit exceeded
            retry_after = int(response.headers.get("Retry-After", 60))
            logger.warning(f"Rate limited. Retry after {retry_after}s")
            time.sleep(retry_after)
        
        else:
            raise Exception(f"API error: {response.status_code}")
    
    raise Exception("Max retries exceeded")
```

**Step 3: Response Header Monitoring**
```python
# Log rate limit info on every request
remaining = response.headers.get("X-RateLimit-Remaining")
reset = response.headers.get("X-RateLimit-Reset")
logger.info(f"Rate limit: {remaining} remaining, resets at {reset}")
```

#### 3. Database Connection Security

**Threat:** Postgres credentials exposed in code

**Mitigation:**
```python
# .env file
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=pipeone_warehouse
POSTGRES_USER=pipeone_user
POSTGRES_PASSWORD=secure_password_here

# Application code
import psycopg2
conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT"),
    database=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD")
)
```

#### 4. SQL Injection Prevention

**Threat:** User input in SQL queries could execute arbitrary commands

**Mitigation:** Always use parameterized queries
```python
# ❌ VULNERABLE
query = f"INSERT INTO events VALUES ('{event_id}', '{repo_name}')"

# ✅ SAFE
query = "INSERT INTO events (event_id, repo_name) VALUES (%s, %s)"
cursor.execute(query, (event_id, repo_name))
```

### Risk Register

| Risk | Likelihood | Impact | Mitigation | Status |
|------|------------|--------|------------|--------|
| API token leaked in Git | Medium | Critical | `.gitignore` + `.env` pattern | ✅ Implemented |
| Rate limit exceeded | High | High | Proactive checking + exponential backoff | ✅ Implemented |
| Duplicate data ingestion | Medium | Medium | PRIMARY KEY constraint on `event_id` | ✅ Implemented |
| Database connection failure | Low | High | Retry logic + connection pooling | ⏳ Planned Week 2 |
| Disk space exhaustion | Low | Medium | Monitor table size + retention policy | ⏳ Planned Week 3 |

---

## Deployment Architecture

### Local Development Setup (Week 1)

**Prerequisites:**
- Docker Desktop installed and running
- Python 3.11+ with pip
- Git configured
- GitHub account with PAT generated

**Setup Commands:**
```bash
# 1. Clone repository
git clone https://github.com/Diw696/pipeone-github-analytics.git
cd pipeone-github-analytics

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure secrets
cp .env.example .env
# Edit .env and add GITHUB_TOKEN=your_token_here

# 5. Start PostgreSQL
docker-compose up -d

# 6. Initialize database schema
python scripts/init_db.py  # Creates github_events_raw table

# 7. Run ingestion
python src/ingestion/github_client.py
```

### Docker Compose Configuration

**File:** `docker-compose.yml`

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:15-alpine
    container_name: pipeone_postgres
    environment:
      POSTGRES_DB: pipeone_warehouse
      POSTGRES_USER: pipeone_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}  # Loaded from .env
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pipeone_user -d pipeone_warehouse"]
      interval: 10s
      timeout: 5s
      retries: 5

  pgadmin:  # Optional: Web UI for database management
    image: dpage/pgadmin4:latest
    container_name: pipeone_pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@pipeone.local
      PGADMIN_DEFAULT_PASSWORD: ${PGADMIN_PASSWORD}
    ports:
      - "5050:80"
    depends_on:
      - postgres

volumes:
  postgres_data:
    driver: local
```

**Benefits:**
- Single `docker-compose up -d` starts entire data infrastructure
- Data persists across container restarts via Docker volumes
- Health checks ensure Postgres is ready before ingestion starts
- pgAdmin provides GUI for manual data inspection

---

## Testing Strategy (Week 1 Scope)

### Manual Verification Tests

**Test 1: API Client Authentication**
```bash
python -c "from src.ingestion.github_client import GitHubClient; client = GitHubClient(); print(client.check_rate_limit())"
# Expected: JSON with rate limit info (remaining > 0)
```

**Test 2: Idempotency Check**
```sql
-- Run ingestion script twice
-- python src/ingestion/github_client.py
-- python src/ingestion/github_client.py

-- Verify no duplicates
SELECT event_id, COUNT(*) 
FROM github_events_raw 
GROUP BY event_id 
HAVING COUNT(*) > 1;
-- Expected: 0 rows (no duplicates)
```

**Test 3: Data Quality Validation**
```sql
-- Check for NULL values in critical columns
SELECT COUNT(*) FROM github_events_raw WHERE event_id IS NULL;  -- Expected: 0
SELECT COUNT(*) FROM github_events_raw WHERE event_payload IS NULL;  -- Expected: 0
SELECT COUNT(*) FROM github_events_raw WHERE repo_name NOT LIKE '%/%';  -- Expected: 0
```

**Test 4: Rate Limit Backoff Simulation**
```python
# Manually set rate limit to 0 in mock
# Observe logs for "Rate limit low" warning
# Verify script sleeps until reset time
```

### Automated Testing (Future)

**Week 2+ Goals:**
- Unit tests with `pytest` (API client methods)
- Integration tests (database connection, insertion)
- Mock GitHub API responses with `responses` library
- CI/CD pipeline with GitHub Actions

---

## Success Metrics & Monitoring

### Week 1 Deliverables

**Functional Requirements:**
- [x] API client successfully authenticates with GitHub
- [ ] Events ingested from all 3 target repositories
- [ ] Zero duplicate events in database (verified via COUNT query)
- [ ] Rate limit handling prevents 403 errors
- [ ] `.env` file not present in Git history

**Non-Functional Requirements:**
- [ ] Ingestion script completes in < 5 minutes for 300 events
- [ ] Database size < 50 MB after initial load
- [ ] No hardcoded credentials in any `.py` file
- [ ] README instructions reproducible on fresh machine

### Observability (Basic)

**Logging Standards:**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/ingestion.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"Fetching events for repo: {repo_name}")
logger.warning(f"Rate limit remaining: {remaining}")
logger.error(f"Database insertion failed: {error}")
```

**Key Metrics to Log:**
- Events fetched per repository
- Events inserted (new) vs. skipped (duplicates)
- Rate limit remaining after each request
- Execution time per repository
- Database connection errors

---

## Future Enhancements (Post-Week 1)

### Week 2: Data Transformations with dbt

**Silver Layer Tables:**
- `stg_push_events` - Parsed commits with file changes
- `stg_pull_requests` - PR lifecycle tracking (open → merged/closed)
- `stg_issue_events` - Issue creation and resolution times

**dbt Features:**
- Incremental models (process only new `event_id` values)
- Data quality tests (unique, not_null, relationships)
- Documentation generation with lineage graphs

### Week 3: Historical Data Backfill

**Challenge:** GitHub API only returns last 90 days of events

**Solution:**
- Daily scheduled runs to capture all new events
- Archive old events to cold storage (S3/GCS) after 1 year
- Integrate GitHub Contributors API for developer leaderboard

### Week 4+: Analytics & Dashboards

**Gold Layer Tables:**
- `repo_activity_daily` - Daily commit counts, PR velocity
- `developer_contributions` - Top contributors by event type
- `open_source_velocity` - Trending repositories, community engagement

**Streamlit Dashboard:**
- Real-time activity heatmaps
- Repository comparison charts
- Developer leaderboards


**Review Criteria:**
- [ ] Architecture is sound for Week 1 scope
- [ ] Security measures are adequate (token protection, SQL injection prevention)
- [ ] Schema design supports future analytics needs
- [ ] Tech stack choices are justified
- [ ] Risk mitigations are clearly defined

---

## Appendix

### Glossary

**Idempotency:** Property where running the same operation multiple times produces the same result as running it once (prevents duplicate data).

**JSONB:** PostgreSQL's binary JSON datatype; supports indexing and efficient queries on nested fields.

**Rate Limiting:** API throttling mechanism to prevent abuse; GitHub allows 5000 requests/hour for authenticated users.

**Bronze/Silver/Gold:** Data maturity layers: Bronze = raw, Silver = cleaned, Gold = analytics-ready.

**Primary Key:** Database constraint ensuring column values are unique and not null; enforces idempotency in our design.

### References

- [GitHub Events API Documentation](https://docs.github.com/en/rest/activity/events)
- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/current/datatype-json.html)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Python requests Library](https://requests.readthedocs.io/)
- [Rate Limit Best Practices](https://docs.github.com/en/rest/guides/best-practices-for-integrators#dealing-with-rate-limits)

---

**Document End**  
**Next Review:** End of Week 1 (June 27, 2026)  
**Version Control:** Track changes in Git commit history
