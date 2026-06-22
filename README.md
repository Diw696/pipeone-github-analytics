# PipeOne: GitHub DevActivity Analytics Pipeline

> **A Production-Grade ETL Pipeline for Open-Source Intelligence & Repository Health Tracking**  
> CSE Data Engineering & AI Internship Project | PulseMetrics Startup Challenge

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![dbt](https://img.shields.io/badge/dbt-postgres-FF694B.svg)](https://www.getdbt.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B.svg)](https://streamlit.io/)
[![GitHub API](https://img.shields.io/badge/GitHub-Events_API-181717.svg)](https://docs.github.com/en/rest/activity/events)

---

## 📋 Business Scenario

**PulseMetrics Junior Data Engineer Challenge**

PulseMetrics is a fast-growing analytics startup serving SMBs with actionable insights from external APIs. As part of the **H1: APIs to Warehouse** implementation track, this project demonstrates end-to-end pipeline engineering capabilities:

- **Objective:** Ingest public GitHub event streams (commits, pushes, pull requests, issues) from the GitHub Events API, transform them into analytical models, and deliver insights for tracking repository health and open-source velocity
- **Target Users:** Tech organizations, DevOps teams, engineering managers, and open-source program offices monitoring developer activity and project trends
- **Success Criteria:** Automated, scalable pipeline handling high-volume JSON payloads with incremental processing and analytics-ready data models for BI consumption

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────┐
│     GitHub Events API       │ (Public event streams: commits, PRs, issues)
└──────────────┬──────────────┘
               │ HTTP Requests (JSON Payloads)
               ▼
┌─────────────────────────────┐
│      Ingestion Layer        │ Python Scripts (src/ingestion/)
│                             │ - GitHub API Client
└──────────────┬──────────────┘ - Event Schema Parsing
               │                - Rate Limit Handling
               │ Raw JSON Events
               ▼
┌─────────────────────────────┐
│      PostgreSQL Warehouse   │ Docker Container
│                             │ - Raw Layer (bronze): github_events_raw
└──────────────┬──────────────┘ - Staging (silver): parsed events
               │                - Analytics (gold): aggregated metrics
               ▼
┌─────────────────────────────┐
│        dbt Models           │ dbt-postgres (dbt_project/)
│                             │ - Event type transformations
└──────────────┬──────────────┘ - Incremental processing
               │                - Repository health metrics
               │ Analytics Tables
               ▼
┌─────────────────────────────┐
│     Streamlit Dashboard     │ (src/dashboard/)
│                             │ - Repo activity trends
└─────────────────────────────┘ - Developer contribution maps
                                - Open-source velocity KPIs
```

---

## 🛠️ Tech Stack

| Layer              | Technology          | Purpose                                           |
|--------------------|---------------------|---------------------------------------------------|
| **Data Ingestion** | Python 3.9+         | GitHub API extraction, JSON parsing, pagination   |
| **Orchestration**  | Docker Compose      | Containerized services & dependency management    |
| **Data Warehouse** | PostgreSQL          | JSONB storage, relational models, ACID compliance |
| **Transformation** | dbt-postgres        | Incremental ELT, event deduplication, aggregations|
| **Visualization**  | Streamlit           | Interactive DevActivity analytics dashboard       |
| **Version Control**| Git/GitHub          | Collaboration & CI/CD readiness                   |

---

## 📂 Project Structure

```
pipeone-github-analytics/
│
├── src/
│   ├── ingestion/              # GitHub API data extraction
│   │   ├── github_client.py    # GitHub Events API connector
│   │   ├── event_extractors.py # Event type-specific parsers
│   │   └── schema_validators.py# JSON schema validation
│   │
│   └── dashboard/              # Streamlit analytics frontend
│       ├── app.py              # Main dashboard application
│       └── components/         # Reusable visualization components
│
├── dbt_project/                # dbt transformation models
│   ├── models/
│   │   ├── staging/            # Silver layer: parsed GitHub events
│   │   │   ├── stg_push_events.sql
│   │   │   ├── stg_pull_requests.sql
│   │   │   └── stg_issue_events.sql
│   │   └── analytics/          # Gold layer: repository metrics
│   │       ├── repo_activity_daily.sql
│   │       ├── developer_contributions.sql
│   │       └── open_source_velocity.sql
│   ├── tests/                  # Data quality tests
│   └── dbt_project.yml         # dbt configuration
│
├── docs/
│   └── adrs/                   # Architecture Decision Records
│
├── docker-compose.yml          # Multi-container orchestration
├── requirements.txt            # Python dependencies
├── design_doc.md               # Technical design documentation
└── README.md                   # This file
```

---

## 🗓️ 5-Week Milestone Roadmap

**Internship Period:** June 22, 2026 → July 26, 2026

### **Week 1: Foundation & GitHub API Integration** (June 22-28)
- [x] Initialize Git repository & project structure
- [ ] Configure Docker Compose (PostgreSQL + pgAdmin)
- [ ] Implement GitHub Events API client with authentication
- [ ] Handle API rate limiting & pagination for event streams
- [ ] Set up raw JSON ingestion to PostgreSQL (JSONB columns)
- [ ] Document architecture decisions (ADRs)

### **Week 2: Data Warehouse & dbt Setup** (June 29 - July 5)
- [ ] Design event-driven schema (star schema for GitHub events)
- [ ] Create dbt project with staging models for event types
- [ ] Implement bronze → silver transformations (parse nested JSON)
- [ ] Build incremental models to handle large event volumes
- [ ] Add dbt tests for event deduplication and schema validation
- [ ] Generate dbt documentation with lineage graphs

### **Week 3: Analytics Layer & Repository Metrics** (July 6-12)
- [ ] Build gold-layer analytics models (daily/weekly aggregations)
- [ ] Create repository health metrics (commit frequency, PR velocity)
- [ ] Implement developer contribution tracking and leaderboards
- [ ] Add event type breakdown analytics (PushEvent, PullRequestEvent, IssuesEvent)
- [ ] Develop open-source velocity KPIs
- [ ] Set up dbt macros for reusable event parsing logic

### **Week 4: Dashboard Development** (July 13-19)
- [ ] Design Streamlit dashboard UI/UX for DevActivity analytics
- [ ] Connect dashboard to PostgreSQL analytics tables
- [ ] Build interactive visualizations (activity heatmaps, contribution graphs)
- [ ] Implement repository filters, date range selectors, and event type toggles
- [ ] Add real-time refresh capabilities for live GitHub event streams
- [ ] Create developer leaderboard and trending repositories view

### **Week 5: Production Readiness & Documentation** (July 20-26)
- [ ] Implement comprehensive logging & monitoring (event pipeline health)
- [ ] Add error alerting for API failures and data quality issues
- [ ] Optimize incremental dbt runs for performance at scale
- [ ] Write comprehensive README & deployment guide
- [ ] Create demo video showcasing GitHub analytics capabilities
- [ ] Prepare cloud deployment documentation (AWS RDS/GCP Cloud SQL)

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose installed
- Python 3.9+ installed
- Git installed
- GitHub Personal Access Token (PAT) for API authentication ([Generate here](https://github.com/settings/tokens))

### Installation

```bash
# Clone the repository
git clone https://github.com/Diw696/pipeone-weather-pipeline.git
cd pipeone-weather-pipeline

# Set up environment variables
cp .env.example .env
# Edit .env and add your GitHub PAT: GITHUB_TOKEN=your_token_here

# Start Docker containers
docker-compose up -d

# Install Python dependencies
pip install -r requirements.txt

# Run dbt models
cd dbt_project
dbt run --models staging   # Parse raw GitHub events
dbt run --models analytics # Build repository metrics
dbt test

# Launch Streamlit dashboard
streamlit run src/dashboard/app.py
```

---

## 📊 Key Features

- **High-Volume Event Ingestion:** Handles GitHub's public event stream with rate limiting, pagination, and retry logic
- **Incremental Processing:** dbt models configured for efficient incremental runs on large JSON payloads
- **Event Deduplication:** Prevents duplicate processing using GitHub event IDs
- **Repository Health Tracking:** Monitor commit frequency, pull request velocity, and issue resolution metrics
- **Developer Analytics:** Contribution leaderboards, activity heatmaps, and collaboration patterns
- **Open-Source Velocity KPIs:** Track project momentum, community engagement, and development trends
- **Production-Ready Architecture:** Docker containerization, structured logging, and monitoring capabilities

---

## 📖 Documentation

- **[Design Document](design_doc.md):** Technical architecture and implementation details
- **[ADRs](docs/adrs/):** Architecture Decision Records for key design choices
- **[dbt Docs](dbt_project/target/index.html):** Auto-generated data lineage (run `dbt docs generate`)

---

## 👨‍💻 Author

**Diwakar Kaushik**  
CSE Data Engineering & AI Student | Lovely Professional University

- 📧 Email: diwakar.kaushik@example.com
- 💼 LinkedIn: [linkedin.com/in/diwakar-kaushik](https://linkedin.com/in/diwakar-kaushik)
- 🐙 GitHub: [@Diw696](https://github.com/Diw696)

---

## 📝 License

This project is developed as part of an academic internship program. All rights reserved.

---

## 🙏 Acknowledgments

- **PulseMetrics** for providing the internship challenge framework
- **Lovely Professional University** for academic guidance
- **GitHub** for providing the Events API and comprehensive documentation
- **dbt Labs** for modern data transformation tooling

---

**Status:** 🚧 Week 1 of 5 - Foundation Phase  
**Last Updated:** June 22, 2026
