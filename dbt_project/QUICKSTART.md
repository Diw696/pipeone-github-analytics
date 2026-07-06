# dbt Quick Start Guide

**Goal:** Get dbt working in under 5 minutes

---

## Prerequisites

✅ PostgreSQL running (Week 1 setup)  
✅ dbt-postgres installed (`pip install -r requirements.txt`)  
✅ You know your PostgreSQL password (from `.env` file)

---

## Step 1: Install profiles.yml (1 minute)

**Option A: Automated (Windows PowerShell)**

```powershell
cd dbt_project
.\setup_dbt_profile.ps1
```

**Option B: Manual**

```powershell
# Create directory
mkdir $env:USERPROFILE\.dbt

# Copy template
copy dbt_project\profiles.yml.example $env:USERPROFILE\.dbt\profiles.yml
```

---

## Step 2: Update Password (1 minute)

1. Open `C:\Users\asus\.dbt\profiles.yml`
2. Find line: `password: your_secure_password_here`
3. Replace with your actual password (from `.env` → `POSTGRES_PASSWORD`)
4. Save file

**Example:**
```yaml
# Before
password: your_secure_password_here

# After (use your real password)
password: myActualPassword123
```

---

## Step 3: Test Connection (1 minute)

```bash
cd dbt_project
dbt debug
```

**Expected output:**
```
12:09:00  Connection test: [OK connection ok]
12:09:00  All checks passed!
```

✅ **Success!** You're ready to build models.

---

## Step 4: Understand What You Built (2 minutes)

### File Structure

```
dbt_project/
├── dbt_project.yml          → Project config (name, profile, paths)
├── profiles.yml.example     → Connection template
├── models/                  → Put SQL files here (empty for now)
├── tests/                   → Data quality tests (empty for now)
└── README_SETUP.md          → Full documentation
```

### Key Files

**`dbt_project.yml`** - Lives inside project, committed to Git
- Project name: `pipeone_dbt`
- Which profile to use: `pipeone`
- Where to find models, tests, etc.

**`~/.dbt/profiles.yml`** - Lives outside project, **NOT** committed to Git
- Database credentials
- Host, port, username, password
- Target schema: `dbt_dev`

---

## Troubleshooting

### Error: "Could not find profile named 'pipeone'"

**Fix:** profiles.yml doesn't exist or is in wrong location

```powershell
# Check if file exists
Test-Path $env:USERPROFILE\.dbt\profiles.yml

# Should return: True
# If False, run setup script again
```

### Error: "password authentication failed"

**Fix:** Wrong password in profiles.yml

1. Check `.env` for correct password: `POSTGRES_PASSWORD=...`
2. Update `~/.dbt/profiles.yml` with that password
3. Run `dbt debug` again

### Error: "could not connect to server"

**Fix:** PostgreSQL isn't running

```bash
# Start PostgreSQL
docker-compose up -d

# Verify it's running
docker ps

# Should show: pipeone-postgres container
```

---

## What's Next?

**Day 1 (Today):** Infrastructure setup ✅  
**Day 2 (Next):** Create first staging model (`stg_push_events.sql`)

Read these docs:
- **Full setup guide:** `README_SETUP.md`
- **Architecture explained:** `../docs/WEEK2_ARCHITECTURE.md`
- **Summary of Day 1:** `../WEEK2_DAY1_SUMMARY.md`

---

## Quick Reference

### Common Commands

```bash
# Test connection
dbt debug

# Run all models
dbt run

# Run specific model
dbt run --models stg_push_events

# Generate documentation
dbt docs generate

# Serve docs site
dbt docs serve
```

### File Locations

| File | Location | Committed to Git? |
|------|----------|-------------------|
| dbt_project.yml | `dbt_project/` | ✅ Yes |
| profiles.yml | `~/.dbt/` | ❌ No (contains secrets) |
| models/ | `dbt_project/models/` | ✅ Yes |
| target/ | `dbt_project/target/` | ❌ No (build artifacts) |

---

**Status:** Setup complete! 🎉  
**Next:** Build your first transformation model
