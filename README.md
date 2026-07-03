# PipeOne: GitHub DevActivity Analytics Pipeline

> **Week 1 Internship Project: Building an API-to-Warehouse Data Pipeline**  
> CSE Data Engineering & AI Student | PulseMetrics Startup Challenge

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg)](https://www.postgresql.org/)
[![GitHub API](https://img.shields.io/badge/GitHub-Events_API-181717.svg)](https://docs.github.com/en/rest/activity/events)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📋 What Is This Project?

**Developer:** Diwakar Kaushik  
**Project:** PipeOne  
**Segment:** Data Platform Engineering - GitHub Analytics  
**Problem:** An automated data engineering pipeline that extracts live GitHub events and stores them inside PostgreSQL for future analytics

This is a learning project focused on understanding the fundamentals of data engineering: extracting data from APIs and storing it in a warehouse. The goal for Week 1 is simple:

- **Objective:** Pull GitHub event data from 3 target open-source repositories and land the raw JSON into PostgreSQL
- **Focus:** Learn how each tool in the stack works and why it matters
- **Deliverable:** Working data flow from GitHub API → PostgreSQL, with ability to explain the tech choices

This is NOT about building production-grade analytics, dashboards, or complex transformations yet. Week 1 is about foundations.

---

## � Target Repositories

This pipeline tracks activity from these 3 major open-source projects:

1. **[facebook/react](https://github.com/facebook/react)** - A JavaScript library for building user interfaces
2. **[microsoft/vscode](https://github.com/microsoft/vscode)** - Visual Studio Code source repository
3. **[vercel/next.js](https://github.com/vercel/next.js)** - High-activity modern web framework

These repositories were chosen for their high activity levels and diversity in technology stacks.

---

## 🏗️ Week 1 Architecture (Simple)

```
┌─────────────────────────────┐
│     GitHub Events API       │ (Public events for 3 repos)
└──────────────┬──────────────┘
               │ HTTP GET requests
               ▼
┌─────────────────────────────┐
│   Python Script             │ (src/ingestion/github_client.py)
│   (github_client.py)        │ - Authenticate with token
└──────────────┬──────────────┘ - Fetch JSON events
               │ Raw JSON
               ▼
┌─────────────────────────────┐
│   PostgreSQL Database       │ (Docker container)
│   (github_events_raw table) │ - Store JSON as-is
└─────────────────────────────┘ - One raw table for now
```

**That's it for Week 1.** No dbt, no Streamlit, no transformations yet.

---

## 🛠️ Tech Stack (Week 1 Scope)

| Tool               | Why I Picked It                                    | What Breaks If I Remove It                          |
|--------------------|----------------------------------------------------|-----------------------------------------------------|
| **Python 3.11+**    | Standard for data engineering, great libraries     | Can't call APIs or process data without a language |
| **requests**       | Makes HTTP calls simple and reliable               | Can't fetch data from GitHub API                   |
| **python-dotenv**  | Keeps secrets out of code (security best practice) | Would have to hardcode token (security risk!)       |
| **PostgreSQL**     | Industry-standard relational database, supports JSON | No place to store data persistently               |
| **Docker Compose** | Run Postgres locally without manual setup          | Would need to install/configure Postgres manually   |
| **Git/GitHub**     | Version control and collaboration                  | Can't track changes or share code                   |

**Not using this week:** dbt (no transformations yet), Streamlit (no dashboard yet), Airflow (no orchestration yet)

---

## 📂 Project Structure (Current State)

```
pipeone-github-analytics/
│
├── src/
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── github_client.py    # ✅ API client + DB integration
│   └── database/
│       ├── __init__.py
│       └── init_db.py           # ✅ Schema initialization
│
├── docs/
│   ├── design_doc.md            # ✅ Week 1 technical design
│   └── roadmap_3rd_year.md      # Future vision (not Week 1)
│
├── .env                         # ✅ Secrets (not committed)
├── .env.example                 # ✅ Template for .env
├── .gitignore                   # ✅ Protects secrets
├── docker-compose.yml           # ✅ Postgres container config
├── requirements.txt             # ✅ Python dependencies
├── test_database.py             # ✅ Connection test
├── verify_pipeline.py           # ✅ Data verification
├── RUN_PIPELINE.md              # ✅ Execution guide
├── WEEK1_SUBMISSION.md          # ✅ Internship submission
└── README.md                    # ✅ This file
```

**Not created yet:** dbt_project/, dashboard/, event parsers, transformations

---

## Week 1 Goals (June 22-27, 2026)

- [x] Docker Compose: Postgres running locally
- [x] Python script: pull events from GitHub API for 3 chosen repos
- [x] Land raw JSON into Postgres (one raw table with JSONB)
- [x] README explains: what does each tool do, why did I pick it
- [x] Database verification script with formatted output
- [x] Design doc ready for mentor review

**Week 1 Status:** ✅ Complete  
**Submission:** `WEEK1_SUBMISSION.md`

> Full roadmap and "dream" architecture (dbt, dashboard, streaming) is in `docs/roadmap_3rd_year.md` — not Week 1 scope.

---

## 🚀 Quick Start (Week 1)

### Prerequisites

- Docker & Docker Compose installed
- Python 3.11+ installed
- Git installed
- GitHub Personal Access Token ([Generate here](https://github.com/settings/tokens) - needs `public_repo` scope)

### Setup Steps

```bash
# 1. Clone the repository
git clone https://github.com/Diw696/pipeone-github-analytics.git
cd pipeone-github-analytics

# 2. Set up environment variables
cp .env.example .env
# Edit .env and add your GitHub token: GITHUB_TOKEN=your_token_here

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Configure secrets
cp .env.example .env
# Edit .env: add GITHUB_TOKEN and POSTGRES_PASSWORD

# 5. Start PostgreSQL
docker-compose up -d

# 6. Initialize database schema
python src/database/init_db.py

# 7. Run the pipeline
python src/ingestion/github_client.py

# 8. Verify data
python verify_pipeline.py
```

---

## � Learning Resources

- **[GitHub Events API Docs](https://docs.github.com/en/rest/activity/events)** - Understanding event types and structure
- **[PostgreSQL JSON Functions](https://www.postgresql.org/docs/current/functions-json.html)** - Working with JSONB data
- **[Docker Compose Docs](https://docs.docker.com/compose/)** - Container orchestration basics
- **[Future Roadmap](docs/roadmap_3rd_year.md)** - Where this project could go (3rd year vision)

---

## 💡 What I Learned This Week (Week 1)

**Docker Containers vs. Installation**  
I used to think Docker was just "virtualization." Now I understand it's about packaging dependencies. Running PostgreSQL in a container means I don't need to install Postgres on my laptop — the container has everything. `docker-compose up` and it's ready. If I mess up, `docker-compose down` wipes it clean.

**PostgreSQL vs. Database Clients**  
I initially confused PostgreSQL (the database engine) with psql (the command-line client). PostgreSQL stores the data. psql is just one way to talk to it. Others include pgAdmin (GUI) or psycopg2 (Python). The database doesn't care which client connects.

**JSONB is Not Just JSON**  
GitHub returns JSON, and I could store it as TEXT. But JSONB is binary-encoded JSON that PostgreSQL can index and query efficiently. Using JSONB lets me run `WHERE raw_payload->>'type' = 'PushEvent'` without parsing strings. Tradeoff: JSONB takes slightly more space but queries are 10x faster.

**Idempotency is a Design Choice, Not Magic**  
Pipelines will re-run (crashes, retries, scheduled jobs). Using `event_id` as PRIMARY KEY + `ON CONFLICT DO NOTHING` means I can run the pipeline 100 times and still have exactly 90 events — no duplicates, no errors. The schema makes it safe.

**Environment Variables Are Security Boundaries**  
Once a secret is in Git history, `.gitignore` doesn't help — you have to rotate the token. That's why `.env` must be in `.gitignore` from the first commit. I set this up before adding my GitHub token, so my repository has zero credential leaks.

---

## 👨‍💻 Author

**Diwakar Kaushik**  
CSE Data Engineering & AI Student | Lovely Professional University

- 📧 Email: devkaushik6906@gmail.com
- 💼 LinkedIn: [linkedin.com/in/diwakar-kaushik](https://www.linkedin.com/in/diwakar-kaushik-a40b65310/)
- 🐙 GitHub: [@Diw696](https://github.com/Diw696/pipeone-github-analytics)

---

## 📝 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

**MIT License Summary:**
- ✅ Free to use, modify, and distribute
- ✅ Can be used commercially
- ⚠️ Provided "as-is" without warranty
- 📋 Must include copyright notice in copies

---

**Current Status:** ✅ Week 1 Deliverable Completed - Pipeline Operational  
**Last Updated:** July 3, 2026  
**Data Ingested:** 188 events across 3 repositories (Successfully ingests live GitHub events from three repositories. Numebr changes as pipeline runs)
**Next Milestone:** dbt transformations (Week 2)
