# PipeOne: Complete Pipeline Execution Guide

## 🎯 Week 1 Goal
Ingest GitHub events from 3 repositories → Store in PostgreSQL with idempotency

---

## 📋 Prerequisites Checklist

- [ ] Docker Desktop installed and running
- [ ] Python 3.11+ installed
- [ ] Git configured
- [ ] GitHub Personal Access Token generated

---

## 🚀 Step-by-Step Execution

### **Step 1: Install Dependencies**
```bash
pip install -r requirements.txt
```

**Verify:**
```bash
python test_setup.py
```

---

### **Step 2: Start PostgreSQL**
```bash
docker-compose up -d
```

**Verify:**
```bash
docker ps
# Should show: pipeone_postgres container running

python test_database.py
```

---

### **Step 3: Initialize Database Schema**
```bash
python src/database/init_db.py
```

**Expected Output:**
```
============================================================
PipeOne Database Initialization
============================================================
✓ Database connection established
✓ Table github_events_raw created successfully
✓ Index idx_repo_event_type created successfully
✓ Database initialization complete!
```

---

### **Step 4: Run the Full Pipeline**
```bash
python src/ingestion/github_client.py
```

**Expected Output:**
```
============================================================
PROCESSING REPOSITORY: facebook/react
============================================================
✓ Fetched 30 events from GitHub API
  Rate limit remaining: 4998
✓ Database write: 30 new, 0 duplicates

============================================================
PROCESSING REPOSITORY: microsoft/vscode
============================================================
✓ Fetched 30 events from GitHub API
  Rate limit remaining: 4997
✓ Database write: 30 new, 0 duplicates

============================================================
PROCESSING REPOSITORY: vercel/next.js
============================================================
✓ Fetched 30 events from GitHub API
  Rate limit remaining: 4996
✓ Database write: 30 new, 0 duplicates

============================================================
PIPELINE EXECUTION SUMMARY
============================================================
Total events fetched: 90
Total events inserted: 90
Total duplicates skipped: 0
Success rate: 100.0%
============================================================
```

---

### **Step 5: Verify Data in Database**
```bash
python verify_pipeline.py
```

**Expected Output:**
```
============================================================
DATABASE VERIFICATION
============================================================

✓ Total events in database: 90

Events by repository:
  microsoft/vscode: 30 events
  facebook/react: 30 events
  vercel/next.js: 30 events

Top 5 event types:
  PushEvent: 45 events
  PullRequestEvent: 20 events
  IssuesEvent: 15 events
  WatchEvent: 7 events
  CreateEvent: 3 events

✓ Duplicate check: 0 duplicates found (should be 0)

============================================================
VERIFICATION COMPLETE
============================================================

🎉 Success! Data is flowing: GitHub API → PostgreSQL
```

---

## 🔄 Testing Idempotency

Run the pipeline again to verify duplicates are skipped:

```bash
python src/ingestion/github_client.py
```

**Expected Second Run:**
```
============================================================
PIPELINE EXECUTION SUMMARY
============================================================
Total events fetched: 90
Total events inserted: 0
Total duplicates skipped: 90
Success rate: 0.0%
============================================================
```

✅ **This is correct!** All events already exist, so they're safely skipped.

---

## 🗄️ Manual Database Inspection

### Using psql:
```bash
docker exec -it pipeone_postgres psql -U pipeone_user -d pipeone_warehouse
```

### Useful Queries:
```sql
-- View all events
SELECT event_id, repo_name, event_type, fetched_at 
FROM github_events_raw 
ORDER BY fetched_at DESC 
LIMIT 10;

-- Count by repository
SELECT repo_name, COUNT(*) 
FROM github_events_raw 
GROUP BY repo_name;

-- Query JSONB payload
SELECT 
    event_id,
    repo_name,
    raw_payload->>'type' as event_type,
    raw_payload->'actor'->>'login' as actor
FROM github_events_raw 
LIMIT 5;

-- Exit psql
\q
```

---

## ⚠️ Troubleshooting

### Issue: "GITHUB_TOKEN not found"
**Solution:**
```bash
cp .env.example .env
# Edit .env and add your GitHub token
```

### Issue: "POSTGRES_PASSWORD not found"
**Solution:**
```bash
# Edit .env and set a password
POSTGRES_PASSWORD=your_secure_password_here
```

### Issue: "Connection refused" to PostgreSQL
**Solution:**
```bash
docker-compose down
docker-compose up -d
# Wait 10 seconds for Postgres to start
python test_database.py
```

### Issue: "Table does not exist"
**Solution:**
```bash
python src/database/init_db.py
```

---

## 📊 Week 1 Success Criteria

- [x] GitHub API client authenticates successfully
- [x] Events ingested from all 3 repos (react, vscode, next.js)
- [x] Zero duplicate events (idempotency via PRIMARY KEY)
- [x] Rate limit handling prevents 403 errors
- [x] No credentials committed to Git (`.env` in `.gitignore`)
- [x] Data persists in PostgreSQL (verified via queries)

---

## 🎉 What We've Built

```
GitHub API → Python Client → PostgreSQL
    ↓             ↓              ↓
3 Repos      fetch_events()   github_events_raw
             save_to_db()     (90 events stored)
             idempotency      (duplicates skipped)
```

**Next Steps (Week 2+):**
- dbt transformations (Silver/Gold layers)
- Event type parsing
- Analytics dashboard (Streamlit)

See `docs/roadmap_3rd_year.md` for full vision.

---

**Last Updated:** June 24, 2026  
**Pipeline Status:** ✅ Operational
