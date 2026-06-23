# PipeOne: GitHub DevActivity Analytics Pipeline

> **Week 1 Internship Project: Building an API-to-Warehouse Data Pipeline**  
> CSE Data Engineering & AI Student | PulseMetrics Startup Challenge

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg)](https://www.postgresql.org/)
[![GitHub API](https://img.shields.io/badge/GitHub-Events_API-181717.svg)](https://docs.github.com/en/rest/activity/events)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📋 What Is This Project?

**PulseMetrics Junior Data Engineer Challenge - Week 1**

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
3. **[automattic/wp-calypso](https://github.com/automattic/wp-calypso)** - The JavaScript and API powered WordPress.com

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
| **Python 3.9+**    | Standard for data engineering, great libraries     | Can't call APIs or process data without a language |
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
│   └── ingestion/
│       ├── __init__.py
│       └── github_client.py    # ✅ DONE: API client with auth day 2
│
├── docs/
│   ├── adrs/                   # Architecture decisions (to be added)
│   └── roadmap_3rd_year.md     # Future vision (not Week 1 scope)
│
├── .env                        # ✅ DONE: Secrets (not committed) day 2
├── .env.example                # ✅ DONE: Template for .env day 2
├── .gitignore                  # ✅ DONE: Protects secrets day 2
├── docker-compose.yml          # ✅TODO: Postgres container config day 2
├── requirements.txt            # ✅ DONE: Python dependencies day 2
└── README.md                   # ✅ DONE: This file
```

**Not created yet:** dbt_project/, dashboard/, event parsers, transformations

---

## Week 1 Goals (29 Jun – 3 Jul)

- [ ] Docker Compose: Postgres running locally - DONE on 23-06-2026
- [ ] Python script: pull events from GitHub API for 3-5 chosen repos
- [ ] Land raw JSON into Postgres (one raw table is enough)
- [ ] README explains: what does each tool do, why did I pick it, what breaks if I remove it
- [ ] Friday demo: show data flowing + explain tech stack (3 min)

> Full roadmap and "dream" architecture (dbt, dashboard, streaming) is in `docs/roadmap_3rd_year.md` — not Week 1 scope.

---

## 🚀 Quick Start (Week 1)

### Prerequisites

- Docker & Docker Compose installed
- Python 3.9+ installed
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

# 4. Start PostgreSQL (TODO: need to create docker-compose.yml first)
docker-compose up -d

# 5. Test the API client
python src/ingestion/github_client.py
```

---

## � Learning Resources

- **[GitHub Events API Docs](https://docs.github.com/en/rest/activity/events)** - Understanding event types and structure
- **[PostgreSQL JSON Functions](https://www.postgresql.org/docs/current/functions-json.html)** - Working with JSONB data
- **[Docker Compose Docs](https://docs.docker.com/compose/)** - Container orchestration basics
- **[Future Roadmap](docs/roadmap_3rd_year.md)** - Where this project could go (3rd year vision)

---

## 👨‍💻 Author

**Diwakar Kaushik**  
CSE Data Engineering & AI Student | Lovely Professional University

- 📧 Email: diwakar.kaushik@example.com
- 💼 LinkedIn: [linkedin.com/in/diwakar-kaushik](https://linkedin.com/in/diwakar-kaushik)
- 🐙 GitHub: [@Diw696](https://github.com/Diw696)

---

## 📝 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

**MIT License Summary:**
- ✅ Free to use, modify, and distribute
- ✅ Can be used commercially
- ⚠️ Provided "as-is" without warranty
- 📋 Must include copyright notice in copies

---

## 🙏 Acknowledgments

- **PulseMetrics** for the internship challenge framework
- **Lovely Professional University** for academic guidance and support
- **GitHub** for providing free public API access
- **Open-source communities** behind React, VSCode, and WP-Calypso for building in public

---

**Current Status:** 🚧 Week 1 - Building Foundation  
**Last Updated:** June 23, 2026  
**Next Milestone:** Docker Compose + Postgres setup
