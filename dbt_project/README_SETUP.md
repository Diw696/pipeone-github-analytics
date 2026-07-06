# Week 2 - Day 1: dbt Infrastructure Setup

**Status:** Infrastructure only - NO models, transformations, or tests yet  
**Goal:** Get dbt installed and connected to PostgreSQL

---

## What We're Building

This is **ONLY** the foundation work for dbt. We're setting up the tools so that next we can build transformation models.

Think of it like installing a toolbox before building furniture. Today = toolbox. Tomorrow = furniture.

---

## Step 1: Verify dbt Installation ✅

dbt-postgres==1.7.4 has been added to `requirements.txt` and installed.

Verify it's working:

```bash
dbt --version
```

**Expected output:**
```
Core:
  - installed: 1.7.4
Plugins:
  - postgres: 1.7.4
```

---

## Step 2: Understanding the dbt Project Structure

Your `dbt_project/` folder now has this structure:

```
dbt_project/
├── dbt_project.yml          # Project configuration (name, version, paths)
├── profiles.yml.example     # Database connection template
├── setup_dbt_profile.ps1    # Helper script to install profiles.yml
├── README_SETUP.md          # This file
├── models/                  # Future: SQL transformation models (empty for now)
├── analyses/                # Future: Ad-hoc analysis queries (empty for now)
├── tests/                   # Future: Data quality tests (empty for now)
├── seeds/                   # Future: CSV reference data (empty for now)
├── macros/                  # Future: Reusable SQL functions (empty for now)
└── snapshots/               # Future: Slowly changing dimensions (empty for now)
```

**What each file/folder does:**

- **`dbt_project.yml`** - The "config file" for your dbt project. It tells dbt:
  - Project name: `pipeone_dbt`
  - Where to find models, tests, seeds, etc.
  - Which database profile to use: `pipeone`

- **`profiles.yml.example`** - Template for database connection credentials. This tells dbt:
  - Database type: PostgreSQL
  - Host, port, database name, user, password
  - Target schema for transformed data

- **`models/`** - Will contain SQL files that transform raw data (Week 2 Day 2+)
- **`tests/`** - Will contain data quality checks (Week 2 Day 3+)
- Other folders: for advanced dbt features (Week 3+)

---

## Step 3: Set Up Database Connection

dbt needs to know HOW to connect to PostgreSQL. This configuration lives in `~/.dbt/profiles.yml`.

### Why profiles.yml Lives Outside the Project

**Question:** Why isn't `profiles.yml` inside the `dbt_project/` folder like everything else?

**Answer:** Security. The profiles.yml file contains your database password. If it were inside the project folder, you might accidentally commit it to Git and expose your credentials.

By keeping it in `~/.dbt/` (your user home directory), it stays local to your machine and never gets committed to version control.

Think of it like this:
- `.env` (in project) = secrets for the ingestion script
- `profiles.yml` (in ~/.dbt/) = secrets for dbt

Both are gitignored, but profiles.yml gets an extra layer of protection by living outside the repo entirely.

### Install profiles.yml

**Option A: Use the helper script (recommended)**

```bash
cd dbt_project
.\setup_dbt_profile.ps1
```

This will:
1. Create `~/.dbt/` directory if it doesn't exist
2. Copy `profiles.yml.example` to `~/.dbt/profiles.yml`
3. Remind you to update the password

**Option B: Manual copy**

```bash
# Create directory
mkdir $env:USERPROFILE\.dbt

# Copy file
copy dbt_project\profiles.yml.example $env:USERPROFILE\.dbt\profiles.yml
```

### Update the Password

1. Open `C:\Users\asus\.dbt\profiles.yml` in your text editor
2. Find the line: `password: your_secure_password_here`
3. Replace with your actual PostgreSQL password (same one from `.env` file - variable `POSTGRES_PASSWORD`)
4. Save the file

**Example:**

```yaml
# Before
password: your_secure_password_here

# After (use your actual password)
password: mySecureP@ssw0rd123
```

---

## Step 4: Test the Connection

Run this command from the `dbt_project/` directory:

```bash
cd dbt_project
dbt debug
```

### What `dbt debug` Does

This command performs a series of checks to verify everything is configured correctly:

1. **Configuration check** - Is dbt_project.yml valid?
2. **Connection check** - Can dbt read profiles.yml?
3. **Database connection test** - Can dbt reach PostgreSQL?
4. **Credential validation** - Are username/password correct?
5. **Schema check** - Does the target schema exist (or can dbt create it)?

### Expected Output (Success)

```
12:09:00  Running with dbt=1.7.4
12:09:00  dbt version: 1.7.4
12:09:00  python version: 3.11.x
12:09:00  python path: C:\Users\asus\AppData\Local\...
12:09:00  os info: Windows-10-...
12:09:00  Using profiles.yml file at C:\Users\asus\.dbt\profiles.yml
12:09:00  Using dbt_project.yml file at C:\Users\asus\Desktop\Pipeone\dbt_project\dbt_project.yml
12:09:00  
12:09:00  Configuration:
12:09:00    profiles.yml file [OK found and valid]
12:09:00    dbt_project.yml file [OK found and valid]
12:09:00  
12:09:00  Required dependencies:
12:09:00   - git [OK found]
12:09:00  
12:09:00  Connection:
12:09:00    host: localhost
12:09:00    port: 5432
12:09:00    user: pipeone_user
12:09:00    database: pipeone_warehouse
12:09:00    schema: dbt_dev
12:09:00    search_path: None
12:09:00    keepalives_idle: 0
12:09:00    Connection test: [OK connection ok]
12:09:00  
12:09:00  All checks passed!
```

**What each section means:**

- **Configuration** - dbt found both yml files and they're valid YAML
- **Required dependencies** - Git is installed (needed for dbt packages)
- **Connection** - Shows the exact connection parameters dbt will use
- **Connection test** - dbt successfully connected to PostgreSQL

### Troubleshooting Common Errors

**Error 1: "Could not find profile named 'pipeone'"**

**Cause:** profiles.yml doesn't exist or is in the wrong location

**Fix:**
```bash
# Check if file exists
Test-Path $env:USERPROFILE\.dbt\profiles.yml

# If False, run the setup script again
.\setup_dbt_profile.ps1
```

---

**Error 2: "password authentication failed for user 'pipeone_user'"**

**Cause:** Wrong password in profiles.yml

**Fix:**
1. Check your `.env` file for the correct `POSTGRES_PASSWORD`
2. Update `~/.dbt/profiles.yml` with the correct password
3. Run `dbt debug` again

---

**Error 3: "could not connect to server: Connection refused"**

**Cause:** PostgreSQL Docker container is not running

**Fix:**
```bash
# Start PostgreSQL
docker-compose up -d

# Verify it's running
docker ps

# Wait 5 seconds, then try dbt debug again
dbt debug
```

---

**Error 4: "database 'pipeone_warehouse' does not exist"**

**Cause:** Database hasn't been created yet

**Fix:**
```bash
# Run the database initialization script
python src/database/init_db.py

# Then try dbt debug again
dbt debug
```

---

## Step 5: Understanding profiles.yml Fields

Let's break down what each field in profiles.yml means:

```yaml
pipeone:                    # Profile name (matches "profile" in dbt_project.yml)
  target: dev               # Which output to use by default (dev or prod)
  outputs:
    dev:                    # Development environment configuration
      type: postgres        # Database type (postgres, snowflake, bigquery, etc.)
      host: localhost       # Where PostgreSQL is running
      user: pipeone_user    # Database username
      password: ***         # Database password (keep this secret!)
      port: 5432            # PostgreSQL default port
      dbname: pipeone_warehouse  # Database name
      schema: dbt_dev       # Schema where dbt will create tables/views
      threads: 4            # Number of parallel queries dbt can run
      keepalives_idle: 0    # TCP keepalive setting (0 = use system default)
      connect_timeout: 10   # Seconds to wait before timing out
      search_path: public   # PostgreSQL search path
```

**Deep dive on key fields:**

### `schema: dbt_dev`

This is WHERE dbt will create your transformed tables and views.

- Raw data lives in: `public.github_events_raw` (from Week 1 ingestion)
- dbt transformations will live in: `dbt_dev.stg_push_events`, `dbt_dev.stg_pull_requests`, etc.

Using a separate schema keeps raw data and transformed data organized:

```
pipeone_warehouse (database)
├── public (schema)
│   └── github_events_raw (table) ← Week 1 ingestion writes here
└── dbt_dev (schema)
    ├── stg_push_events (view) ← dbt will create this (Week 2)
    ├── stg_pull_requests (view)
    └── daily_repo_activity (table)
```

### `threads: 4`

dbt can run multiple SQL queries in parallel to speed up transformations.

- 1 thread = queries run one at a time (slow)
- 4 threads = dbt can run 4 queries simultaneously (faster)

For Week 2 with only a few models, threads doesn't matter much. But when you have 50+ models, this becomes important.

### `target: dev`

You can have multiple environments (dev, prod, staging). The `target` field tells dbt which one to use by default.

- `dev` - For local development and testing (uses `schema: dbt_dev`)
- `prod` - For production deployments (uses `schema: dbt_prod`)

You can switch targets with:
```bash
dbt run --target prod
```

---

## What We've Accomplished (Day 1)

✅ **Installed dbt-postgres** (added to requirements.txt)  
✅ **Created dbt project structure** (dbt_project/, folders, dbt_project.yml)  
✅ **Set up database connection** (profiles.yml configured)  
✅ **Tested connection** (dbt debug passes)  
✅ **Understood the architecture** (read documentation, explained every field)

---

## What's Next (Day 2+)

❌ **Create staging models** - Parse event types from JSONB  
❌ **Add data quality tests** - Validate no nulls, check relationships  
❌ **Build analytics models** - Aggregations for dashboard  
❌ **Set up CI/CD** - Automate dbt runs

**Important:** We are NOT doing any of that today. Day 1 = infrastructure only.

---

## Interview Questions (Test Your Understanding)

**Question 1:** Why does profiles.yml live in `~/.dbt/` instead of inside `dbt_project/`?

<details>
<summary>Click to reveal answer</summary>

**Answer:** Security. profiles.yml contains database passwords. By keeping it outside the project directory (in ~/.dbt/), we ensure it never gets accidentally committed to Git. This is similar to how .env files are gitignored, but profiles.yml gets an extra layer of protection by living outside the repo entirely.

</details>

---

**Question 2:** What is the difference between `dbt_project.yml` and `profiles.yml`?

<details>
<summary>Click to reveal answer</summary>

**Answer:**

- **dbt_project.yml** = WHAT to build (project name, where models are, configuration for transformations)
- **profiles.yml** = WHERE to build it (database connection details: host, port, credentials)

Think of it like a recipe:
- dbt_project.yml = the recipe (ingredients, steps, instructions)
- profiles.yml = the kitchen location (which oven, which pantry)

</details>

---

**Question 3:** You run `dbt debug` and get: "Could not find profile named 'pipeone'". What's wrong?

<details>
<summary>Click to reveal answer</summary>

**Answer:** profiles.yml either doesn't exist or is in the wrong location. The file must be at `~/.dbt/profiles.yml` (Windows: `C:\Users\asus\.dbt\profiles.yml`). Run the setup script (`.\setup_dbt_profile.ps1`) to create it in the correct location.

</details>

---

## Git Commit Message (Suggested)

```
feat(week2): Add dbt infrastructure setup

- Add dbt-postgres==1.7.4 to requirements.txt
- Create dbt_project/ directory structure
- Configure dbt_project.yml with project settings
- Add profiles.yml.example template for database connection
- Create setup_dbt_profile.ps1 helper script
- Add comprehensive setup documentation

Week 2 Day 1 deliverable: dbt infrastructure ready for model development.
No models or transformations included - pure infrastructure setup.
```

---

**Status:** Week 2 Day 1 Complete ✅  
**Next:** Day 2 - Create first staging model  
**Current Focus:** Infrastructure only - transformation work begins tomorrow
