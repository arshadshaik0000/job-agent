# AUTONOMOUS JOB DISCOVERY AGENT — COMPLETE PROJECT NARRATIVE

> **Purpose of this document:** A full, detailed walkthrough of every file, every function, every data flow, and every known consideration in this project. Written so that any LLM or developer can understand the entire system from scratch and debug any problem.

---

## 1. PROJECT OVERVIEW

**What it is:** A Python-based autonomous agent that continuously discovers, scrapes, filters, and notifies the user about entry-level/intern software engineering jobs from across the internet.

**Who it's for:** Arshad Uzzama Shaik — 2025 B.Tech CSE (AI & ML) graduate looking for junior/intern roles globally.

**How it works:** A scheduled pipeline runs every 60 minutes via APScheduler:

```
SCRAPE → FILTER → SAVE → NOTIFY
```

The scraping layer aggregates jobs from 7+ sources:
- **JobSpy** (LinkedIn, Indeed, Glassdoor)
- **Greenhouse** (72+ startup boards)
- **Lever** (50+ startup boards)
- **Ashby** (65+ startup boards via GraphQL)
- **Workable** (56+ companies)
- **Web Discovery** (DuckDuckGo → career page crawling)

The filtering layer applies 4 sequential checks:
1. Visa/sponsorship scoring
2. Rule-based title + JD scoring
3. Years-of-experience extraction
4. Local AI validation via Ollama

**Tech stack:**
- Python 3.10+ (macOS)
- python-jobspy (LinkedIn + Indeed + Glassdoor aggregation)
- requests (ATS API calls to Greenhouse, Lever, Workable)
- BeautifulSoup4 (HTML parsing for job descriptions)
- aiohttp (async career page crawling)
- duckduckgo-search (web discovery — no API key needed)
- Ollama + qwen2.5:7b-instruct (local AI validation — optional, no cloud costs)
- SQLite (jobs.db — zero config database)
- python-telegram-bot (real-time Telegram alerts)
- APScheduler (blocking scheduler, 60-minute interval)
- openpyxl (Excel export)
- python-dotenv (environment variables)

---

## 2. FILE-BY-FILE BREAKDOWN

### 2.1 Root Files

---

#### `.env` (16 lines)

Stores all secrets and user configuration. Loaded by `python-dotenv` in `config.py`.

**Contents:**
```
GEMINI_API_KEY=<key>          ← NOT USED ANYWHERE in code currently
TELEGRAM_TOKEN=<token>
TELEGRAM_CHAT_ID=<chat_id>
APPLICANT_NAME=Arshad Uzzama Shaik
APPLICANT_EMAIL=arshaduzzamashaik@gmail.com
APPLICANT_PHONE=7702503405
APPLICANT_LINKEDIN=https://www.linkedin.com/in/arshad-uzzama-shaik-3b767424b/
APPLICANT_GITHUB=https://github.com/arshadshaik0000
APPLICANT_LOCATION=Guntur, Andhra Pradesh, India
```

**Key notes:**
- `GEMINI_API_KEY` is present but never loaded or used by any module
- Only `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` are consumed by `config.py`
- `APPLICANT_*` fields are present for future resume/application features

---

#### `config.py` (94 lines)

Central configuration file. Loaded by `main.py` and `modules/scraper.py`.

**What it defines:**
1. **API Keys:** `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` — loaded from `.env`
2. **Database:** `DB_PATH = "jobs.db"`
3. **SEARCH_TERMS:** 10 search query strings:
   - `"graduate software engineer"`, `"junior software engineer"`, `"entry level software engineer"`, `"junior backend engineer"`, `"junior full stack engineer"`, `"ai engineer junior"`, `"associate software engineer"`, `"software engineer new grad"`, `"junior platform engineer"`, `"ml engineer entry level"`
4. **SEARCH_LOCATIONS:** 10 target regions:
   - India, United Kingdom, Germany, Netherlands, Ireland, UAE, Sweden, Poland, Spain, Remote
5. **REJECT_TITLE_KEYWORDS:** 10 words to reject:
   - senior, staff, principal, lead, manager, director, architect, vp, head of, chief
6. **SPONSORSHIP_KEYWORDS:** 9 visa/sponsorship phrases:
   - visa sponsorship, sponsorship available, relocation support, work visa, sponsor visa, relocation package, relocation assistance, international candidates welcome, we sponsor
7. **NON_ENGLISH_KEYWORDS:** 7 language rejection phrases:
   - german required, japanese required, mandarin required, french required, fluent german, native japanese, dutch required
8. **GREENHOUSE_COMPANIES:** 25 company slugs:
   - stripe, cloudflare, datadog, notion, figma, plaid, coinbase, canonical, elastic, snyk, hashicorp, mongodb, cockroachlabs, squarespace, airtable, gitlab, hubspot, twilio, discord, reddit, brex, ramp, affirm, instacart, doordash
9. **LEVER_COMPANIES:** 3 company slugs:
   - netlify, postman, webflow

---

#### `requirements.txt` (7 lines)

Lean dependency list:
```
python-jobspy
python-telegram-bot
APScheduler
python-dotenv
pandas
requests
beautifulsoup4
```

**Note:** Additional dependencies like `aiohttp`, `openpyxl`, and `duckduckgo-search` are used by submodules in `modules/` but are not listed here. They would need to be installed separately if those modules are activated.

---

#### `main.py` (175 lines)

The entry point and brain of the agent. Uses APScheduler for periodic execution.

**Functions:**

1. **`contains_sponsorship(text)`** (line 29)
   - Checks if text mentions visa sponsorship using `SPONSORSHIP_KEYWORDS` from config
   - Simple case-insensitive substring matching

2. **`requires_non_english(text)`** (line 35)
   - Checks if job requires a non-English language using `NON_ENGLISH_KEYWORDS`

3. **`is_entry_level(title)`** (line 41)
   - Rejects senior/lead/director roles using `REJECT_TITLE_KEYWORDS`
   - Returns `True` if NONE of the reject keywords are in the title

4. **`is_valid_job(job)`** (lines 47-76)
   - Main filter function with three-tier logic:
     - ❌ Non-English required → skip
     - ❌ Senior/Lead/Director → skip
     - 🇮🇳 India → allow all remaining entry-level jobs
     - 🌍 International → ONLY if sponsorship is mentioned in description
     - ❓ Sponsorship unclear → SKIP

5. **`scan_jobs()`** (lines 83-146)
   - One complete scan cycle
   - Calls `search_jobs()` from `modules/scraper.py` to get all jobs
   - For each job: `is_valid_job()` → check `job_exists()` → enrich (set visa_sponsorship, status, hr_score, notes) → `save_job()` → `notify_job_found()`
   - Sleeps 2 seconds between Telegram sends (rate limiting)
   - Prints a summary at the end: new jobs, filtered, duplicates

6. **`__main__` block** (lines 153-175)
   - Prints startup banner with sources and regions
   - Calls `init_db()` to initialize SQLite
   - Runs `scan_jobs()` immediately
   - Sets up `BlockingScheduler` with 60-minute interval
   - Catches `KeyboardInterrupt` for clean shutdown

**Data flow in `scan_jobs()`:**
```
search_jobs() → is_valid_job() → job_exists() → save_job() → notify_job_found()
     ↓                ↓               ↓              ↓              ↓
  scraper.py      main.py filters  tracker.py    tracker.py    notifier.py
```

---

### 2.2 Core Modules

---

#### `modules/scraper.py` (280 lines)

Multi-source job aggregator. The main scraping engine.

**Country extraction:**
- `CITY_TO_COUNTRY` dict maps 40+ city/country keywords to standardized country names
- `extract_country(location_str)` — Finds the first matching keyword in a free-text location string

**Source 1 — JobSpy (lines 59-106):**
- `search_jobspy()` — Scrapes LinkedIn, Indeed, Glassdoor using the `jobspy` library
- Iterates through `SEARCH_LOCATIONS × SEARCH_TERMS` (10 × 10 = 100 combinations)
- For each combination: `scrape_jobs(site_name=["linkedin","indeed","glassdoor"], results_wanted=15, hours_old=72)`
- Fetches LinkedIn descriptions too (`linkedin_fetch_description=True`)
- Sleeps 2 seconds between queries
- Returns list of standardized job dicts

**Source 2 — Greenhouse (lines 112-171):**
- `search_greenhouse()` — Hits `https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true`
- Uses 25 companies from `config.GREENHOUSE_COMPANIES`
- Parses HTML descriptions via BeautifulSoup
- `extract_country()` to normalize locations
- Sleeps 1 second between companies

**Source 3 — Lever (lines 177-230):**
- `search_lever()` — Hits `https://api.lever.co/v0/postings/{company}?mode=json`
- Uses 3 companies from `config.LEVER_COMPANIES`
- Converts Lever's epoch-ms timestamps to date strings
- Sleeps 1 second between companies

**Aggregator — `search_jobs()` (lines 236-270):**
- Calls all 3 sources in try/except blocks (one failing doesn't kill the others)
- Deduplicates by `job_url` using a set
- Returns unique job list

---

#### `modules/tracker.py` (76 lines)

SQLite database layer. Simple, focused, and clean.

**Database:** `jobs.db` (path from `config.DB_PATH`)

**Schema (`init_db()` creates):**
```sql
CREATE TABLE IF NOT EXISTS jobs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    job_title         TEXT,
    company           TEXT,
    country           TEXT,
    job_url           TEXT UNIQUE,    -- deduplication key
    visa_sponsorship  TEXT,
    hr_score          REAL,
    status            TEXT DEFAULT 'discovered',
    resume_version    TEXT,
    skills_emphasized TEXT,
    date_found        TEXT,
    date_applied      TEXT,
    jd_content        TEXT,
    notes             TEXT
);
```

**Functions:**
- `init_db()` — Creates table, prints confirmation
- `job_exists(job_url)` — Returns True if URL already in DB
- `save_job(job_data)` — INSERT with all fields, uses `datetime.now()` for `date_found`, handles IntegrityError (duplicate URL)

**Characteristics:**
- Each function opens/closes its own SQLite connection
- No connection pooling (fine for single-threaded use)
- Uses UNIQUE constraint on `job_url` for deduplication

---

#### `modules/notifier.py` (60 lines)

Sends Telegram notifications using `python-telegram-bot`.

**Functions:**

1. **`_send(text)`** — Internal async function, creates a `Bot` instance and sends message with Markdown parsing
2. **`send_message(text)`** — Sync wrapper, calls `asyncio.run(_send(text))`
3. **`notify_job_found(job)`** — Formats a detailed job card message:
   ```
   🚀 *New Job Found!*
   
   🏢 *Company:* Stripe
   💼 *Role:* Junior Software Engineer
   🌍 *Location:* Bangalore, India
   🗺 *Country:* India
   ✈️ *Visa:* Not Required (India) 🇮🇳
   📅 *Posted:* 2026-02-24
   📡 *Source:* Greenhouse
   🔗 [Apply Here](https://...)
   ```

**Visa display logic:**
- `sponsored` → "Sponsorship Available ✅"
- India jobs → "Not Required (India) 🇮🇳"
- All else → "Unknown"

---

#### `modules/exporter.py` (65 lines)

Exports today's jobs to an Excel spreadsheet.

**Function:** `export_jobs_to_excel(filepath="jobs_export.xlsx")`
- Queries for jobs where `DATE(date_found) = DATE('now','localtime')`
- Creates workbook with columns: Job Title, Company, Country, Visa, HR Score, Status, Resume Version, Skills, Date Found, Date Applied, URL
- Auto-adjusts column widths (capped at 50 chars)
- Requires `openpyxl` package

---

### 2.3 Extended Modules (Advanced Pipeline)

These modules provide additional capabilities for a more advanced pipeline. They're defined in `modules/` subpackages but are NOT directly called from the current `main.py`. The current `main.py` uses its own simpler filter functions. These modules can be activated by importing and using them in a more advanced version of the pipeline.

---

#### `modules/crawling/career_crawler.py` (243 lines)

Async career page crawler using aiohttp.

**How it works:**
1. For each domain, tries 10 common career paths (`/careers`, `/jobs`, `/join-us`, etc.)
2. If no direct paths work, fetches homepage and looks for career links in HTML
3. For each found career page, extracts individual job posting links using URL patterns
4. Returns a dict mapping `domain → [job_urls]`

**Key components:**
- `CAREER_PATHS` — 18 common career page URL paths
- `CAREER_LINK_PATTERNS` — 7 regex patterns for career page link text
- `JOB_LINK_PATTERNS` — 9 regex patterns for job posting URLs (including ATS-specific patterns like Greenhouse, Lever, Ashby, Workable)
- `MAX_CONCURRENT = 10` — Semaphore limit for concurrent crawls
- `TIMEOUT = 15` — Per-request timeout

**Functions:**
- `fetch_url()` — Async GET with content-type validation
- `find_career_links()` / `find_job_links()` — BeautifulSoup-based link extraction
- `detect_career_page()` — Tries common paths + homepage fallback
- `crawl_domain()` — Full crawl pipeline for one domain
- `crawl_career_pages()` — Concurrent crawl of multiple domains
- `run_crawler()` — Synchronous wrapper via `asyncio.run()`

---

#### `modules/discovery/web_discovery.py` (308 lines)

Discovers new company career domains using DuckDuckGo search.

**Key data structures:**
- `ROLE_KEYWORDS` — 16 role search terms (software engineer, backend developer, AI engineer, etc.)
- `LEVEL_KEYWORDS` — 11 seniority level terms (junior, graduate, intern, fresher, etc.)
- `COUNTRIES` — 12 target countries
- `SEARCH_SUFFIXES` — 6 career page suffixes
- `SKIP_DOMAINS` — 27 domains to skip (job boards, social media)
- `ATS_DOMAINS` — 14 known ATS platform domains

**Functions:**
- `generate_search_queries()` — Generates randomized queries using 3 strategies
- `discover_domains()` — Searches DDG, extracts domains, saves new ones to SQLite cache
- SQLite cache functions: `init_domains_table()`, `domain_exists()`, `save_domain()`, `get_uncrawled_domains()`, `mark_crawled()`
- Helper functions: `extract_domain()`, `is_valid_domain()`, `is_ats_domain()`

**Note:** `init_domains_table()` is called at module import time (line 307), which means it runs even when the module is just imported.

---

#### `modules/filtering/visa_filter.py` (111 lines)

Visa/sponsorship scoring for international job postings.

**Scoring:**
- 29 positive keywords (e.g., "visa sponsorship available" +3, "we sponsor" +2, "relocation support" +1)
- 14 negative keywords (e.g., "no sponsorship" -5, "cannot sponsor" -5, "citizens only" -5)

**Auto-pass rules:**
- India jobs (15 city/country keywords) → auto-pass with score 99
- Remote internships → auto-pass with score 50

**Decision logic:**
- Score ≥ 1 → PASS (sponsorship likely)
- Score < -2 → REJECT (no sponsorship)
- -2 ≤ Score ≤ 0 → REJECT (no sponsorship info for international role)

---

#### `modules/filtering/rule_scoring.py` (161 lines)

Weighted keyword scoring system for job titles and descriptions.

**Title scoring (45 keywords):**
- Positive: `internship` (+4), `intern` (+4), `graduate` (+3), `junior` (+3), `associate` (+2), `entry level` (+2), `software engineer` (+1), `developer` (+1), etc.
- Negative: `senior` (-6), `staff` (-6), `principal` (-6), `lead` (-6), `director` (-6), `manager` (-6), etc.

**JD scoring (31 keywords):**
- Positive: `internship` (+3), `0-2 years` (+2), `new grad` (+2), `entry level` (+1), etc.
- Negative: `5+ years` (-4), `7+ years` (-4), `technical leadership` (-3), `managed a team` (-4), etc.

**Accept threshold:** Score ≥ 2

**Functions:**
- `score_job(title, desc)` → returns (score, breakdown_list)
- `passes_rule_filter(title, desc)` → returns (accepted_bool, score, breakdown)

---

#### `modules/filtering/experience_parser.py` (89 lines)

Extracts years-of-experience requirements from JD text using 6 regex patterns.

**Patterns match:**
- `5+ years` / `5+ yrs`
- `5-7 years`
- `minimum 5 years` / `at least 5 years`
- `5 years of experience`
- `5 years' experience` (possessive)
- `experience: 5 years`

**Rules:**
- Internship titles → auto-pass
- Max detected years ≥ 3 → REJECT
- Otherwise → PASS

---

#### `modules/filtering/ollama_validator.py` (258 lines)

Final AI validation layer using local Ollama LLM.

**How it works:**
1. Computes MD5 hash of `title|description[:500]`
2. Checks SQLite cache — if cached, returns immediately
3. Strips HTML, truncates description to 2000 chars
4. Sends structured prompt to `http://localhost:11434/api/generate`
5. Parses JSON response (handles markdown code blocks, brace extraction)
6. Normalizes decision to ACCEPT/REJECT, caches result
7. If Ollama is offline → fallback: ACCEPT with 30% confidence

**Configuration:**
- `MODEL = "qwen2.5:7b-instruct"`
- `TIMEOUT = 10` seconds
- `MAX_RETRIES = 1`
- `MAX_DESC_LENGTH = 2000` chars

**Prompt tells the AI:**
- Candidate is a 2025 B.Tech CSE (AI & ML) graduate
- ACCEPT: internships, graduate/junior/entry-level (0-2 years)
- REJECT: senior/lead/staff/principal/architect/manager/director, 3+ years experience
- Return JSON: `{"decision": "ACCEPT/REJECT", "confidence": 0-100, "reason": "..."}`

---

#### `modules/parsing/greenhouse.py` (111 lines)

Extended Greenhouse ATS scraper with 72+ companies.

**Categories covered:** AI/ML (OpenAI, Anthropic, Cohere, Mistral, etc.), Dev Tools (Vercel, Supabase, Railway, etc.), Fintech (Stripe, Brex, Mercury, etc.), Cloud/Security (Cloudflare, Datadog, Wiz, etc.), Data (Databricks, dbt-labs, etc.), Productivity (Notion, Figma, Miro, etc.), India (Razorpay, CRED, Groww, etc.)

**API:** `https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true`

---

#### `modules/parsing/lever.py` (121 lines)

Extended Lever ATS scraper with 50+ companies.

**Categories covered:** Big Tech Adjacent (Netflix, Dropbox, Atlassian, etc.), Fintech (Affirm, Klarna, Chime, etc.), Dev/Cloud (DigitalOcean, Airtable, Webflow, etc.), Data (Snowflake, Metabase, etc.), global regions (Israel, India, APAC, Africa)

**API:** `https://api.lever.co/v0/postings/{company}?mode=json`

---

#### `modules/parsing/ashby.py` (134 lines)

Ashby ATS scraper with 65+ companies using GraphQL.

**API:** POST `https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams`

**Unique features:**
- Uses GraphQL query to fetch job postings
- Filters to only `jobPostingState == "Listed"` jobs
- Constructs URLs from `externalLink` or builds from `jobs.ashbyhq.com/{company}/{id}`

---

#### `modules/parsing/workable.py` (117 lines)

Workable ATS scraper with 56+ companies.

**API:** POST `https://apply.workable.com/api/v3/accounts/{company}/jobs`

**Categories covered:** EU Startups, UK Fintech, Nordic, Eastern Europe, MENA, APAC, LATAM, Africa, Japan, Israel, India

---

#### `modules/parsing/generic_html.py` (222 lines)

Universal HTML job page parser using BeautifulSoup heuristics.

**Capabilities:**
- Extracts job title using 6 CSS selectors + aria-label + `<title>` fallback
- Extracts company from Open Graph meta, CSS selectors, or domain name
- Extracts location from 6 CSS selectors + 📍 emoji detection
- Extracts description from 16 CSS selectors in order of specificity
- Detects "Apply" buttons to confirm a page is a job posting
- `parse_job_page(url)` — Full pipeline returning structured dict
- `fetch_full_jd(url)` — Fetches just the description text (used to enrich short JDs)

---

## 3. DATA FLOW

### 3.1 Job Dict Schema

Every job flows through the pipeline as a Python dict:

```python
{
    "job_title":    str,    # e.g., "Junior Software Engineer"
    "company":      str,    # e.g., "Stripe"
    "location":     str,    # e.g., "Bangalore, India"
    "country":      str,    # e.g., "India"
    "job_url":      str,    # Full URL (deduplication key)
    "jd_content":   str,    # Job description text (up to 6000 chars)
    "source":       str,    # "linkedin", "indeed", "glassdoor", "greenhouse", "lever"
    "date_posted":  str,    # "2026-02-24" (may be empty)
}
```

After enrichment in `scan_jobs()`:
```python
{
    "visa_sponsorship": str,  # "sponsored" or "not_required"
    "status":           str,  # "discovered"
    "hr_score":         int,  # 0 (unused placeholder)
    "notes":            str,  # "Source: greenhouse"
}
```

### 3.2 Pipeline Flow

```
main.py: scan_jobs()
├── scraper.py: search_jobs()
│   ├── search_jobspy()          → 100 JobSpy queries → list[dict]
│   ├── search_greenhouse()      → 25 API calls       → list[dict]
│   └── search_lever()           → 3 API calls         → list[dict]
│   └── Deduplicate by URL
│
├── For each job:
│   ├── is_valid_job()           → 3-tier filter
│   │   ├── requires_non_english() → reject if non-English required
│   │   ├── is_entry_level()       → reject senior/lead/director
│   │   ├── India check            → auto-pass
│   │   └── contains_sponsorship() → check for visa mention
│   │
│   ├── tracker.py: job_exists() → skip duplicates
│   ├── tracker.py: save_job()   → INSERT to SQLite
│   └── notifier.py: notify_job_found() → Telegram message
│
└── Print summary + send summary via Telegram
```

---

## 4. DATABASE STATE

The `jobs.db` SQLite file contains the accumulated job history.

**Tables:**
1. `jobs` — All saved jobs with UNIQUE constraint on `job_url`

Additional tables are created by the extended modules if they are imported:
2. `discovered_domains` — Cache of domains found by web discovery
3. `ai_validation_cache` — Cache of Ollama AI decisions

---

## 5. COMPLETE FILE LISTING

```
job-agent/
├── .env                              (16 lines)    Secrets & user config
├── .gitignore                        (13 lines)    Git ignore rules
├── config.py                         (94 lines)    Central configuration
├── jobs.db                           (~7.5 MB)     SQLite database
├── jobs_export.xlsx                  (15 KB)       Latest Excel export
├── main.py                           (175 lines)   Pipeline orchestrator + scheduler
├── PROJECT_NARRATIVE.md              (this file)   Full project walkthrough
├── README.md                         (231 lines)   Project documentation
├── requirements.txt                  (7 lines)     Python dependencies
│
└── modules/
    ├── __init__.py                   (empty)       Package init
    ├── scraper.py                    (280 lines)   Multi-source aggregator (JobSpy + Greenhouse + Lever)
    ├── scraper.py.bak                (41 KB)       OLD monolithic scraper (UNUSED backup)
    ├── tracker.py                    (76 lines)    SQLite database layer
    ├── notifier.py                   (60 lines)    Telegram notifications
    ├── exporter.py                   (65 lines)    Excel export
    │
    ├── crawling/
    │   ├── __init__.py               (55 bytes)    Package init
    │   └── career_crawler.py         (243 lines)   Async career page crawler
    │
    ├── discovery/
    │   ├── __init__.py               (56 bytes)    Package init
    │   └── web_discovery.py          (308 lines)   DuckDuckGo domain discovery
    │
    ├── filtering/
    │   ├── __init__.py               (74 bytes)    Package init
    │   ├── visa_filter.py            (111 lines)   Visa sponsorship scoring
    │   ├── rule_scoring.py           (161 lines)   Weighted keyword scoring
    │   ├── experience_parser.py      (89 lines)    Years-of-experience extraction
    │   └── ollama_validator.py       (258 lines)   Local Ollama AI validation
    │
    └── parsing/
        ├── __init__.py               (62 bytes)    Package init
        ├── greenhouse.py             (111 lines)   Greenhouse ATS parser (72+ companies)
        ├── lever.py                  (121 lines)   Lever ATS parser (50+ companies)
        ├── ashby.py                  (134 lines)   Ashby ATS parser (65+ companies)
        ├── workable.py               (117 lines)   Workable ATS parser (56+ companies)
        └── generic_html.py           (222 lines)   Universal HTML job parser

Active core pipeline: ~656 lines across 5 files (main.py, config.py, scraper.py, tracker.py, notifier.py)
Extended modules: ~1,724 lines across 9 files (available but not in active pipeline)
Total: ~2,380 lines of Python across 14 files
```

---

## 6. HOW TO RUN

```bash
# Clone
git clone https://github.com/arshadshaik0000/job-agent.git
cd job-agent

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure
# Edit .env with your Telegram token and chat ID

# Run
python main.py
# Ctrl+C to stop
```

### Optional: Enable AI Validation Layer

```bash
# Install Ollama (https://ollama.com)
ollama pull qwen2.5:7b-instruct
ollama serve &

# Then integrate ollama_validator.py into the pipeline
```

---

## 7. CONFIGURATION REFERENCE

| Config Variable | Value | Used By |
|----------------|-------|---------|
| `TELEGRAM_TOKEN` | from `.env` | `notifier.py` |
| `TELEGRAM_CHAT_ID` | from `.env` | `notifier.py` |
| `DB_PATH` | `"jobs.db"` | `tracker.py` |
| `SEARCH_TERMS` | 10 keywords | `scraper.py` |
| `SEARCH_LOCATIONS` | 10 regions | `scraper.py` |
| `REJECT_TITLE_KEYWORDS` | 10 words | `main.py` |
| `SPONSORSHIP_KEYWORDS` | 9 phrases | `main.py` |
| `NON_ENGLISH_KEYWORDS` | 7 phrases | `main.py` |
| `GREENHOUSE_COMPANIES` | 25 slugs | `scraper.py` |
| `LEVER_COMPANIES` | 3 slugs | `scraper.py` |

---

*Document generated from complete reading of all source files in the job-agent project. Last updated: 2026-02-25.*
