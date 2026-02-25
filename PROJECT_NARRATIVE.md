# AUTONOMOUS JOB DISCOVERY AGENT — COMPLETE PROJECT NARRATIVE

> **Purpose of this document:** A full, detailed walkthrough of every file, every function, every data flow, and every known issue in this project. Written so that any LLM or developer can understand the entire system from scratch and debug any problem.

---

## 1. PROJECT OVERVIEW

**What it is:** A Python-based autonomous agent that continuously discovers, scrapes, filters, and notifies the user about entry-level/intern software engineering jobs from across the internet.

**Who it's for:** Arshad Uzzama Shaik — 2025 B.Tech CSE (AI & ML) graduate looking for junior/intern roles globally.

**How it works:** A 10-step pipeline runs in an infinite loop (every 120 seconds):

```
DISCOVER → CRAWL → PARSE → RULE SCORE → EXPERIENCE FILTER → VISA FILTER → AI VALIDATE → SAVE → NOTIFY → EXPORT
```

**Tech stack:**
- Python 3.11+ (runs on 3.12.0 via pyenv)
- Ollama + LLaMA 3 (local AI validation — no cloud API costs)
- DuckDuckGo Search (web discovery — no API key needed)
- aiohttp (async career page crawling)
- BeautifulSoup4 (HTML parsing)
- ATS APIs: Greenhouse REST, Lever REST, Ashby GraphQL, Workable REST
- python-jobspy (LinkedIn + Indeed aggregation)
- SQLite (jobs.db — zero config database)
- python-telegram-bot (real-time alerts)
- openpyxl (Excel export)
- python-dotenv (environment variables)

**Runtime:** macOS, Python 3.12.0 via pyenv

---

## 2. FILE-BY-FILE BREAKDOWN

### 2.1 Root Files

---

#### `.env` (18 lines)

Stores all secrets and user configuration. Loaded by `python-dotenv` in `config.py`.

**Contents:**
```
GEMINI_API_KEY=AIzaSyBv41yPHVwrReGxZpJgZf0iEl20nS-D2ms    ← NOT USED ANYWHERE in code currently
TELEGRAM_TOKEN=7729420893:AAHObhEyCqSEDsPpndF5vyrXe501tdtfG-Y
TELEGRAM_CHAT_ID=8110645616
APPLICANT_NAME=Arshad Uzzama Shaik
APPLICANT_EMAIL=arshaduzzamashaik@gmail.com
APPLICANT_PHONE=7702503405
APPLICANT_LINKEDIN=https://www.linkedin.com/in/arshad-uzzama-shaik-3b767424b/
APPLICANT_GITHUB=https://github.com/arshadshaik0000
APPLICANT_LOCATION=Guntur, Andhra Pradesh, India
DAILY_TARGET=250
MIN_HR_SCORE=70
```

**Key notes:**
- `GEMINI_API_KEY` is loaded in `config.py` but never used by any module — it's dead code
- `OLLAMA_MODEL` is NOT in `.env` — it defaults to `llama3:latest` in `config.py`
- `APPLICANT` info is loaded into a dict in `config.py` but is NEVER USED by any module currently — the applicant info is not sent in Telegram messages or anywhere else

---

#### `config.py` (128 lines)

Central configuration file. Loaded by almost every module.

**What it defines:**
1. **API Keys:** `GEMINI_API_KEY`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` — loaded from `.env`
2. **Ollama Settings:** `OLLAMA_MODEL` (default: `llama3:latest`), `OLLAMA_URL` (default: `http://localhost:11434/api/generate`)
3. **Applicant Info:** Dict with name, email, phone, linkedin, github, location, graduation_year (2025), degree — **NOT USED ANYWHERE**
4. **TARGET_ROLES:** 14 role keywords (Software Engineer, Backend Engineer, AI Engineer, etc.)
5. **TARGET_LEVELS:** 11 level keywords (Intern, Junior, Graduate, Fresher, etc.) — **NOT USED in filtering logic** (filtering uses its own hardcoded lists in `rule_scoring.py`)
6. **TECH_STACK:** 22 tech keywords — **NOT USED ANYWHERE** in the codebase
7. **Filtering Thresholds:** `MIN_RULE_SCORE=2`, `MAX_EXPERIENCE_YEARS=3`, `MIN_HR_SCORE=70`, `DAILY_TARGET=250`
8. **Crawler Settings:** `CRAWL_MAX_DOMAINS=30`, `CRAWL_TIMEOUT=15`, `CRAWL_CONCURRENCY=10`, `DISCOVERY_BATCH_SIZE=15`
9. **Scan Settings:** `SCAN_INTERVAL_SECONDS=120`
10. **Paths:** `BASE_RESUME_PATH`, `RESUMES_DIR`, `LOGS_DIR`, `DB_PATH=jobs.db`
11. **JOBSPY_SEARCHES:** 25 search query objects covering India (10), UK (3), Germany (2), Netherlands (1), Ireland (1), UAE (1), Canada (1), Australia (1), Singapore (1), Japan (1), Remote (3)

**Known issues:**
- `TARGET_ROLES`, `TARGET_LEVELS`, `TECH_STACK` are defined but NEVER imported or used by any module
- `APPLICANT` dict is defined but NEVER used
- `MIN_HR_SCORE` and `DAILY_TARGET` are defined but NEVER checked in any logic
- `CRAWL_MAX_DOMAINS` is defined but the actual limit in `main.py` is hardcoded to `20` (line 141)
- `CRAWL_TIMEOUT` is defined but `career_crawler.py` uses its own hardcoded `TIMEOUT=15`
- `BASE_RESUME_PATH`, `RESUMES_DIR`, `LOGS_DIR` are defined but never used

---

#### `requirements.txt` (42 lines)

All pip dependencies. Mix of pinned versions and minimum versions.

**Key dependencies:**
- `python-jobspy==1.1.82` — LinkedIn + Indeed scraper
- `ollama==0.6.1` — Ollama client library (but code uses raw `requests` instead!)
- `python-telegram-bot==22.6` — Telegram Bot API
- `openpyxl==3.1.5` — Excel file creation
- `beautifulsoup4==4.14.3` — HTML parsing
- `aiohttp>=3.9.0` — Async HTTP client
- `duckduckgo-search>=7.0.0` — DuckDuckGo search API
- `requests==2.32.5` — HTTP client (used for ATS APIs and Ollama)
- `playwright==1.58.0` — Browser automation (INSTALLED but NEVER USED in code)
- `redis==7.1.1` — Redis client (INSTALLED but NEVER USED in code)

**Known issues:**
- `ollama` package is installed but the code uses raw `requests.post()` to call the Ollama API instead of the `ollama` library
- `playwright` is installed but never imported or used anywhere
- `redis` is installed but never imported or used anywhere
- These unused dependencies increase install time and size

---

#### `main.py` (369 lines)

The brain of the agent. Orchestrates the entire 10-step pipeline.

**Functions:**

1. **`deduplicate(jobs)`** (lines 29-46)
   - Takes a list of job dicts
   - Deduplicates by both `job_url` and `job_hash` (company+title+country MD5)
   - Returns unique jobs

2. **`collect_all_jobs()`** (lines 51-167)
   - **Steps 1-3** of the pipeline
   - Calls each scraper in try/except blocks (so one failing doesn't kill the pipeline):
     - `scrape_greenhouse()` → ATS REST API
     - `scrape_lever()` → ATS REST API
     - `scrape_ashby()` → ATS GraphQL API
     - `scrape_workable()` → ATS REST API
     - JobSpy (LinkedIn + Indeed) → iterates through 25 `JOBSPY_SEARCHES` from config
     - Web Discovery → `discover_domains()` → `get_uncrawled_domains()` → `run_crawler()` → `parse_job_page()`
   - Each scraper returns `list[dict]` with standardized job schema
   - All jobs are merged into one big list

3. **`filter_jobs(jobs)`** (lines 172-252)
   - **Steps 4-7** of the pipeline
   - For each job:
     - If JD is too short (<300 chars), tries to fetch full JD from the URL via `fetch_full_jd()`
     - **Step 4 — Rule Scoring:** Calls `passes_rule_filter(title, desc)` → weighted keyword scoring
     - **Step 5 — Experience:** Calls `passes_experience_filter(title, desc)` → regex year extraction
     - **Step 6 — Visa:** Calls `check_visa(title, desc, country, is_remote)` → sponsorship scoring
     - **Step 7 — Ollama AI:** Calls `validate_with_ollama(title, desc, job_hash)` → local LLM validation
   - Logs progress every 50 jobs
   - Returns only jobs that pass ALL 4 filters

4. **`process_results(jobs)`** (lines 257-303)
   - **Steps 8-10** of the pipeline
   - For each passed job:
     - **Step 8 — Save:** Checks if URL already exists in DB, saves via `save_job()`
     - **Step 9 — Notify:** Calls `notify_job_found(job)` → sends Telegram message
     - **Step 10 — Export:** Calls `export_jobs_to_excel()` → writes Excel file
   - Sleeps 1 second between Telegram messages (rate limiting)

5. **`scan_jobs()`** (lines 307-339)
   - One complete scan cycle
   - Calls: `collect_all_jobs()` → `deduplicate()` → filter out already-saved → `filter_jobs()` → `process_results()`

6. **`__main__` block** (lines 344-369)
   - Initializes database with `init_db()`
   - Runs `scan_jobs()` in an infinite `while True` loop
   - Sleeps `SCAN_INTERVAL_SECONDS` (120s) between cycles
   - Catches `KeyboardInterrupt` for clean shutdown
   - Catches all other exceptions, logs them, sleeps 30s, and continues

**Known issues:**
- The web discovery `batch_size=10` is hardcoded on line 137, ignoring `DISCOVERY_BATCH_SIZE=15` from config
- The uncrawled domains `limit=20` is hardcoded on line 141, ignoring `CRAWL_MAX_DOMAINS=30` from config
- `time.sleep(1)` between Telegram messages (line 293) means 78 new jobs = 78 seconds of blocking
- The pipeline is synchronous — no async/await in the main loop despite aiohttp being used internally
- `ResourceWarning: unclosed socket` warnings appear in output from the JobSpy library not cleaning up connections properly — this is a python-jobspy library bug, not the agent's fault

---

### 2.2 Module Files

---

#### `modules/__init__.py` (empty)

Makes `modules/` a Python package. No content.

---

#### `modules/tracker.py` (216 lines)

SQLite database layer. All database operations go through this file.

**Database:** `jobs.db` (path from `config.DB_PATH`)

**Tables created by `init_db()`:**

1. **`jobs`** — Main table
   - `id` INTEGER PRIMARY KEY AUTOINCREMENT
   - `job_title` TEXT
   - `company` TEXT
   - `country` TEXT
   - `job_url` TEXT UNIQUE ← dedup key
   - `visa_sponsorship` TEXT
   - `hr_score` REAL
   - `relevance_score` INTEGER DEFAULT 0
   - `status` TEXT DEFAULT 'pending'
   - `resume_version` TEXT
   - `skills_emphasized` TEXT
   - `date_found` TEXT
   - `date_applied` TEXT
   - `jd_content` TEXT
   - `notes` TEXT
   - `source` TEXT DEFAULT ''
   - Has migration code to add `relevance_score` and `source` columns if upgrading from older schema

2. **`daily_stats`** — Daily counters (NOT ACTIVELY POPULATED)
   - `date` TEXT UNIQUE
   - `total_found`, `total_applied`, `india_applied`, `international_applied`, `sponsored_applied`, `manual_review`, `avg_hr_score`, `resumes_created`

3. **`discovered_domains`** — Web discovery cache
   - `domain` TEXT PRIMARY KEY
   - `company_name`, `career_url`, `source_query`, `is_ats`, `last_crawled`, `job_count`, `discovered_at`

4. **`ai_validation_cache`** — Ollama result cache
   - `job_hash` TEXT PRIMARY KEY
   - `decision` TEXT NOT NULL (ACCEPT/REJECT)
   - `confidence` INTEGER
   - `reason` TEXT
   - `validated_at` TEXT

**Functions:**
- `init_db()` — Creates all 4 tables + migrations
- `job_exists(job_url)` — Check if URL is already saved
- `save_job(job_data)` — INSERT with UNIQUE constraint on `job_url`
- `update_job_status(job_url, status, ...)` — Update status to 'applied' etc.
- `update_daily_stats(date, **kwargs)` — **Never called from main.py**
- `get_today_stats()` — **Never called**
- `get_all_applied()` — **Never called**
- `job_hash(job)` — MD5 of `company|title|country`

**Known issues:**
- `daily_stats` table is created but never populated — `update_daily_stats` is never called
- `update_job_status` is defined but never called from `main.py`
- `get_today_stats` and `get_all_applied` are defined but never called
- Each function opens/closes its own SQLite connection — no connection pooling
- No WAL mode — could have locking issues with concurrent access (though currently single-threaded)

---

#### `modules/notifier.py` (33 lines)

Sends Telegram notifications for each new job found.

**Function:** `notify_job_found(job)`
- Loads `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` from `.env` on EVERY call (inefficient)
- Formats a MarkdownV2 message with company, role, location, source, visa, and apply link
- Uses `asyncio.run()` to send via `python-telegram-bot`'s async API
- Has an `esc()` helper that escapes 18 special characters for MarkdownV2

**Message format:**
```
🚀 *New Job Found\!*

🏢 *Company:* OpenAI
💼 *Role:* Software Engineering Intern
🌍 *Location:* San Francisco
📡 *Source:* greenhouse
✈️ *Visa:* unknown
🔗 [Apply Here](https://...)
```

**Known issues:**
- Calls `load_dotenv()` and `os.getenv()` on EVERY single call instead of reading from config once
- Uses `asyncio.run()` inside a synchronous loop — creates a new event loop each time
- No error handling for network failures — exceptions propagate up to `main.py`'s try/except
- Does NOT include the score, AI confidence, or AI reason in the message (those are in `job["notes"]` but not sent)
- The escape function doesn't handle the `\` character itself — could cause double-escape issues

---

#### `modules/exporter.py` (65 lines)

Exports today's jobs to an Excel file.

**Function:** `export_jobs_to_excel(filepath="jobs_export.xlsx")`
- Queries SQLite for jobs where `DATE(date_found) = DATE('now','localtime')`
- Creates an Excel workbook with headers: Job Title, Company, Country, Visa, HR Score, Status, Resume Version, Skills, Date Found, Date Applied, URL
- Auto-adjusts column widths (capped at 50 chars)
- Saves to `jobs_export.xlsx`

**Known issues:**
- Uses `print()` instead of `log.info()` for the export confirmation message
- The date filter `DATE('now','localtime')` may not work correctly across timezone boundaries
- Overwrites the same file every cycle — no daily archiving

---

#### `modules/discovery/web_discovery.py` (308 lines)

Discovers new company career domains using DuckDuckGo search.

**Key data structures:**
- `ROLE_KEYWORDS` — 16 role search terms
- `LEVEL_KEYWORDS` — 11 seniority level terms
- `COUNTRIES` — 12 countries
- `SEARCH_SUFFIXES` — 6 career page suffixes ("careers", "hiring", etc.)
- `SKIP_DOMAINS` — 27 domains to skip (job boards, social media, etc.)
- `ATS_DOMAINS` — 14 known ATS platform domains

**Functions:**

1. **`generate_search_queries(batch_size=20)`**
   - Generates randomized queries using 3 strategies:
     - 1/3: `{level} {role} {suffix}` (e.g., "junior software engineer careers")
     - 1/3: `{level} {role} {country}` (e.g., "intern backend engineer India")
     - Remaining: targeted exact-match queries (hardcoded list of 10)
   - Returns shuffled list of queries

2. **`discover_domains(batch_size=15)`**
   - Creates a `DDGS()` instance
   - For each query: searches DDG with `max_results=10`
   - Extracts domain from each result URL
   - Skips invalid/known-skip domains
   - Saves new domains to SQLite via `save_domain()`
   - Sleeps 1.5s between queries (rate limiting)
   - Returns list of newly discovered domains

3. **SQLite cache functions:** `init_domains_table()`, `domain_exists()`, `save_domain()`, `get_uncrawled_domains()`, `mark_crawled()`

4. **Helper functions:** `extract_domain()`, `is_valid_domain()`, `is_ats_domain()`

**Known issues:**
- `init_domains_table()` is called at module import time (line 307) — this means it runs even when just importing the module (side effect)
- The `discovered_domains` table is created in BOTH `tracker.py` (`init_db()`) AND `web_discovery.py` (`init_domains_table()`) — duplicate table creation
- Sleeps 1.5s per query × 15 queries = ~22.5 seconds minimum per discovery cycle just for rate limiting

---

#### `modules/crawling/career_crawler.py` (243 lines)

Async career page crawler using aiohttp.

**How it works:**
1. For each domain, tries 10 common career paths (`/careers`, `/jobs`, `/join-us`, etc.)
2. If no direct paths work, fetches the homepage and looks for career links in the HTML
3. For each found career page, extracts individual job posting links using URL patterns
4. Returns a dict mapping `domain → [job_urls]`

**Key data structures:**
- `CAREER_PATHS` — 18 common career page URL paths
- `CAREER_LINK_PATTERNS` — 7 regex patterns for career page link text
- `JOB_LINK_PATTERNS` — 9 regex patterns for job posting URLs (including ATS-specific patterns)

**Functions:**
- `fetch_url(session, url)` — Async GET with 15s timeout, validates content-type
- `find_career_links(soup, base_url)` — Finds links to career pages (same-domain or known ATS)
- `find_job_links(soup, base_url)` — Finds individual job posting URLs using regex patterns
- `detect_career_page(session, domain)` — Tries common paths + homepage fallback
- `extract_jobs_from_page(session, career_url)` — Gets job links from a career page
- `crawl_domain(session, domain)` — Full crawl pipeline for one domain
- `crawl_career_pages(domains)` — Async crawl of multiple domains with semaphore (max 10 concurrent)
- `run_crawler(domains)` — Synchronous wrapper (`asyncio.run()`)

**Known issues:**
- `ssl=False` on all connections — disables SSL verification (security concern, but avoids cert errors)
- Hardcoded `MAX_CONCURRENT=10` and `TIMEOUT=15` — ignores config values
- `run_crawler()` calls `asyncio.run()` — can conflict with existing event loops if called from async context
- Only tries first 10 career paths and first 5 career pages per domain — some jobs may be missed

---

#### `modules/parsing/greenhouse.py` (111 lines)

Scrapes jobs from Greenhouse ATS using the public boards API.

**Company list:** 72 companies including OpenAI, Anthropic, Stripe, Vercel, Notion, Figma, Coinbase, Razorpay, etc.

**How it works:**
- For each company, hits `https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true`
- Extracts title, HTML description (converted to text via BeautifulSoup), location, and URL
- Sleeps 0.5s between companies
- Returns standardized job dicts

**Known issues:**
- 72 companies × 0.5s sleep = ~36 seconds minimum per cycle just for Greenhouse
- Some company slugs may be wrong — no validation, just silently skips 404s
- Truncates JD at 6000 chars

---

#### `modules/parsing/lever.py` (121 lines)

Scrapes jobs from Lever ATS using the public postings API.

**Company list:** 50 companies including Netflix, Dropbox, Atlassian, MongoDB, Snowflake, Stripe, etc.

**How it works:**
- For each company, hits `https://api.lever.co/v0/postings/{company}?mode=json`
- Extracts title, URL, description (from `descriptionBody` blocks), and location
- Sleeps 0.5s between companies

**Known issues:**
- The `descriptionBody` parsing logic (lines 93-103) is fragile — the Lever API response format for description varies between companies
- Some companies might not have active Lever boards — silently skipped
- 50 companies × 0.5s = ~25 seconds minimum

---

#### `modules/parsing/ashby.py` (134 lines)

Scrapes jobs from Ashby ATS using the public GraphQL API.

**Company list:** 65 companies including OpenAI, Anthropic, Cursor, Supabase, Linear, Mercury, Brex, etc.

**How it works:**
- For each company, sends a GraphQL query to `https://jobs.ashbyhq.com/api/non-user-graphql`
- Extracts title, HTML description, location, and job URL
- Only includes jobs with `jobPostingState == "Listed"`
- Sleeps 0.5s between companies

**Known issues:**
- Some companies overlap with Greenhouse list (e.g., OpenAI, Anthropic, Cursor, Vercel) — causes duplicate jobs that must be deduped later
- 65 companies × 0.5s = ~32 seconds minimum

---

#### `modules/parsing/workable.py` (117 lines)

Scrapes jobs from Workable ATS using the public jobs API.

**Company list:** 56 companies including Revolut, Monzo, Spotify, GitLab, Razorpay, Freshworks, etc.

**How it works:**
- For each company, POSTs to `https://apply.workable.com/api/v3/accounts/{company}/jobs`
- Extracts title, shortcode (to build URL), location (city + country), and description
- Sleeps 0.5s between companies

**Known issues:**
- The description from the list API is often just a short summary — full JD requires a separate API call (not implemented)
- Some companies overlap with other ATS lists
- 56 companies × 0.5s = ~28 seconds minimum

---

#### `modules/parsing/generic_html.py` (222 lines)

Parses ANY career page on the internet using BeautifulSoup heuristics.

**Functions:**

1. **`fetch_page(url)`** — GET request, parse HTML, remove noise (script, style, nav, header, footer, aside)
2. **`extract_title(soup)`** — Tries 6 CSS selectors, then aria-labels, then `<title>` tag
3. **`extract_company(soup, url)`** — Tries Open Graph meta, CSS selectors, falls back to domain name
4. **`extract_location(soup)`** — Tries 6 CSS selectors, then looks for 📍 emoji
5. **`extract_description(soup)`** — Tries 16 CSS selectors in order of specificity, falls back to full body text
6. **`has_apply_button(soup)`** — Checks for "Apply" buttons/links
7. **`parse_job_page(url)`** — Full pipeline: fetch → extract title/company/location/description → return structured dict
8. **`fetch_full_jd(url)`** — Fetches just the description text (used by `filter_jobs()` to enrich short JDs)

**Known issues:**
- Heuristic-based — will fail on non-standard HTML structures
- `fetch_page()` uses synchronous `requests.get()` — can block for up to 12 seconds per page
- No JavaScript rendering — won't work on SPAs (React/Angular career pages)
- Generic HTML parser is only used for web-discovered domains, not for ATS-scraped jobs

---

#### `modules/filtering/rule_scoring.py` (161 lines)

Weighted keyword scoring system for job titles and descriptions.

**Scoring rules:**

Title Positive (31 keywords): `internship` (+4), `intern` (+4), `graduate` (+3), `junior` (+3), `associate` (+2), `entry level` (+2), `software engineer` (+1), `developer` (+1), etc.

Title Negative (14 keywords): `senior` (-6), `staff` (-6), `principal` (-6), `lead` (-6), `director` (-6), `manager` (-6), etc.

JD Positive (19 keywords): `internship` (+3), `0-2 years` (+2), `new grad` (+2), `entry level` (+1), etc.

JD Negative (12 keywords): `5+ years` (-4), `7+ years` (-4), `technical leadership` (-3), `managed a team` (-4), etc.

**Accept threshold:** Score >= 2

**Functions:**
- `score_job(title, desc)` → returns (score, breakdown_list)
- `passes_rule_filter(title, desc)` → returns (accepted_bool, score, breakdown)

**Known issues:**
- Simple substring matching — `"associate"` matches `"disassociate"`, `"lead"` matches `"misleading"`
- The TITLE_NEGATIVE entry `"lead "` has a trailing space, but `"lead"` at end of title won't match
- Does NOT use `TARGET_ROLES` or `TARGET_LEVELS` from config — has its own hardcoded lists
- No weighting for how many times a keyword appears — single occurrence = same score as 10 occurrences

---

#### `modules/filtering/experience_parser.py` (89 lines)

Extracts years-of-experience requirements from JD text.

**Regex patterns (6):**
- `5+ years` / `5+ yrs`
- `5-7 years`
- `minimum 5 years` / `at least 5 years`
- `5 years of experience`
- `5 years' experience` (possessive)
- `experience: 5 years`

**Rules:**
- Internships (`intern`, `internship`, `trainee`, `apprentice`, `placement`, `co-op`) → **auto-pass** regardless of experience mentioned
- If max detected years >= 3 → **REJECT**
- Otherwise → **PASS**

**Functions:**
- `extract_experience(text)` → returns max years found (0 if none)
- `is_internship_title(title)` → bool
- `passes_experience_filter(title, desc)` → returns (passed, years, reason)

**Known issues:**
- `MAX_EXPERIENCE_YEARS=3` is defined in config but the threshold `>= 3` is hardcoded on line 82
- Matches the FIRST number in patterns like "5-7 years" — takes the lower bound (5), not the range
- Could match false positives in non-experience context (e.g., "Founded 5 years ago")

---

#### `modules/filtering/visa_filter.py` (111 lines)

Scores visa/sponsorship likelihood for international roles.

**Positive signals (29 keywords):** "visa sponsorship available" (+3), "we sponsor" (+2), "relocation support" (+1), etc.

**Negative signals (14 keywords):** "no sponsorship" (-5), "cannot sponsor" (-5), "must have work authorization" (-3), "citizens only" (-5), etc.

**Auto-pass rules:**
- India jobs (15 Indian city/country keywords) → auto-pass with score 99
- Remote internships → auto-pass with score 50

**Decision logic:**
- Score >= 1 → **PASS** (sponsorship likely)
- Score < -2 → **REJECT** (no sponsorship)
- -2 <= Score <= 0 → **REJECT** (no sponsorship info for international role)

**Functions:**
- `check_visa(title, desc, country, is_remote)` → returns (passed, score, reason)

**Known issues:**
- Neutral score (0) for international roles = REJECT — this is aggressive, may reject roles that simply don't mention visa
- The `is_remote` flag is computed in `main.py` by checking if "remote" is in country or title — but many remote roles don't have "remote" in the title

---

#### `modules/filtering/ollama_validator.py` (258 lines)

Final AI validation layer using local Ollama LLM.

**How it works:**
1. Computes an MD5 hash of `title|description[:500]`
2. Checks SQLite cache (`ai_validation_cache` table) — if cached, returns immediately
3. Strips HTML from description, truncates to 2000 chars
4. Builds a structured prompt with rules for the AI
5. Calls Ollama API via `requests.post()` to `http://localhost:11434/api/generate`
6. Parses the JSON response (handles markdown code blocks, brace extraction)
7. Normalizes decision to ACCEPT/REJECT, caches result
8. If Ollama is offline → fallback: ACCEPT with 30% confidence

**Prompt template tells the AI:**
- Candidate is a 2025 B.Tech CSE (AI & ML) graduate
- ACCEPT: internships, graduate/junior/entry-level (0-2 years)
- REJECT: senior/lead/staff/principal/architect/manager/director, 3+ years experience
- Return only JSON: `{"decision": "ACCEPT/REJECT", "confidence": 0-100, "reason": "..."}`

**Functions:**
- `init_ai_cache()` — Creates cache table (also called at import time, line 257)
- `get_cached_result(job_hash)` / `cache_result(job_hash, result)` — SQLite cache ops
- `compute_job_hash(title, desc)` — MD5 of title + first 500 chars
- `strip_html(text)` — BeautifulSoup-based HTML removal
- `parse_ollama_response(text)` — Tries direct JSON, markdown block, brace extraction
- `call_ollama(prompt, retries=1)` — HTTP call with retry logic
- `validate_with_ollama(title, desc, job_hash)` — Full pipeline: cache check → call → cache save → return

**Known issues:**
- Uses raw `requests.post()` instead of the installed `ollama` Python library
- `TIMEOUT=10` seconds is short for LLM inference — may timeout on slower machines
- `MAX_RETRIES=1` — only 2 attempts total
- Fallback is ACCEPT — if Ollama is down, ALL jobs pass AI validation (this is intentional but could flood Telegram)
- The `ai_validation_cache` table is created in BOTH `tracker.py` and `ollama_validator.py`
- Cache hash only uses first 500 chars of description — two jobs with same title and similar first 500 chars will share cache

---

#### `modules/scraper.py.bak` (41,679 bytes)

**A backup file of the original monolithic scraper.** This was the original single-file implementation before the project was refactored into modules. It is NOT used anywhere and can be safely ignored/deleted.

---

## 3. DATA FLOW

### 3.1 Job Dict Schema

Every job flows through the pipeline as a Python dict with these keys:

```python
{
    "job_title": str,           # e.g., "Software Engineering Intern"
    "company": str,             # e.g., "OpenAI"
    "country": str,             # e.g., "San Francisco, CA" or "India"
    "job_url": str,             # Full URL to the job posting
    "jd_content": str,          # Job description text (up to 6000 chars)
    "source": str,              # "greenhouse", "lever", "ashby", "workable", "jobspy", "web_discovery"
    "visa_sponsorship": str,    # "unknown", "sponsored", "not_required"
    "date_found": str,          # "2026-02-19 00:45:00"
    "status": str,              # "found" → "pending" (in DB)
    "hr_score": int/float,      # Always 0 — never calculated
    "notes": str,               # Added by filter: "Score:12 | AI:95% | reason"
    "relevance_score": int,     # Set by filter_jobs()
    "resume_version": str,      # Always "" — never set
    "skills_emphasized": str,   # Always "" — never set
}
```

### 3.2 Pipeline Flow

```
1. collect_all_jobs()
   ├── scrape_greenhouse()     → ~72 API calls → list[dict]
   ├── scrape_lever()          → ~50 API calls → list[dict]
   ├── scrape_ashby()          → ~65 API calls → list[dict]
   ├── scrape_workable()       → ~56 API calls → list[dict]
   ├── JobSpy                  → ~25 searches  → list[dict]
   └── Web Discovery           → DDG search → crawl → parse → list[dict]
   
   Total: ~800-2000 raw jobs per cycle

2. deduplicate(all_jobs)
   → Remove duplicates by URL and hash
   → ~400-800 unique jobs

3. Filter out already-saved (job_exists check)
   → 0-800 unseen jobs (depends on how fresh the DB is)

4. filter_jobs(unseen)
   ├── Rule scoring filter     → rejects ~60% (senior/staff/lead)
   ├── Experience filter       → rejects ~5% (3+ years required)
   ├── Visa filter             → rejects ~10% (no sponsorship)
   └── Ollama AI filter        → rejects ~5% (AI says NOPE)
   
   → ~20-100 jobs pass all filters

5. process_results(passed)
   ├── save_job()              → INSERT into SQLite
   ├── notify_job_found()      → Telegram message
   └── export_jobs_to_excel()  → Excel file
```

---

## 4. DATABASE STATE

The `jobs.db` SQLite file is 2.7 MB, indicating it has accumulated a substantial number of jobs across previous runs.

**Tables:**
1. `jobs` — Contains all saved jobs with deduplication by `job_url` UNIQUE constraint
2. `daily_stats` — Exists but is never populated
3. `discovered_domains` — Cache of all domains found by web discovery
4. `ai_validation_cache` — Cache of Ollama AI decisions to avoid re-processing

---

## 5. KNOWN ISSUES & BUGS

### 5.1 ResourceWarning: Unclosed Sockets

**What you see in output:**
```
ResourceWarning: unclosed <socket.socket fd=26, ...>
ResourceWarning: unclosed transport <_SelectorSocketTransport fd=26>
```

**Cause:** The `python-jobspy` library's internal HTTP client (likely `tls_client` or `httpx`) doesn't properly close socket connections when it finishes. This is a bug in the jobspy library, not in the agent code.

**Impact:** Memory leak over long runs. Sockets accumulate and may hit OS file descriptor limits.

**Fix options:**
1. Suppress warnings: `import warnings; warnings.filterwarnings("ignore", category=ResourceWarning)`
2. Upgrade python-jobspy to a newer version if available
3. Wrap JobSpy calls with explicit cleanup

### 5.2 Unused Config Variables

Many variables in `config.py` are defined but never used:
- `APPLICANT` dict — never referenced
- `TARGET_ROLES`, `TARGET_LEVELS`, `TECH_STACK` — never imported by any module
- `MIN_HR_SCORE`, `DAILY_TARGET` — never checked
- `BASE_RESUME_PATH`, `RESUMES_DIR`, `LOGS_DIR` — never used
- `CRAWL_MAX_DOMAINS`, `CRAWL_TIMEOUT` — ignored (hardcoded values used instead)

### 5.3 Duplicate Table Creation

Both `tracker.py` and `web_discovery.py` create the `discovered_domains` table.
Both `tracker.py` and `ollama_validator.py` create the `ai_validation_cache` table.
This is harmless (CREATE TABLE IF NOT EXISTS) but is code duplication.

### 5.4 Aggressive Visa Filtering

International roles with NO visa information (neutral score of 0) are REJECTED. This means jobs that simply don't mention sponsorship are filtered out, even if they might sponsor.

### 5.5 Ollama Fallback Floods Telegram

If Ollama is offline, the fallback is ACCEPT with 30% confidence. This means ALL jobs that pass the first 3 filters will be saved and sent to Telegram, potentially sending hundreds of notifications.

### 5.6 Synchronous Telegram Sends

`notify_job_found()` calls `asyncio.run()` inside a synchronous loop with `time.sleep(1)` between sends. For 78 new jobs, this takes 78+ seconds of blocking.

### 5.7 Company Overlap Across ATS Parsers

Some companies appear in multiple ATS parser lists (e.g., OpenAI in both Greenhouse and Ashby, Razorpay in Greenhouse/Lever/Workable). The deduplication step handles this by URL, but it means extra API calls are made.

### 5.8 No Persistent Logging to File

All logging goes to stdout only. There's no file handler — if the terminal is closed, logs are lost. `LOGS_DIR` is defined in config but never used.

### 5.9 Unused Dependencies

`playwright`, `redis`, and `ollama` (the library) are installed but never used in the code.

---

## 6. EXECUTION OUTPUT ANALYSIS

From the run output the user showed (piped through 874 lines):

**What happened:**
1. Agent started successfully
2. Scraped all 4 ATS platforms (Greenhouse, Lever, Ashby, Workable)
3. Scraped JobSpy (25 LinkedIn + Indeed searches)
4. Ran web discovery
5. Filtered all collected jobs
6. 78 new jobs passed all filters and were saved
7. 78 Telegram notifications sent (one per second)
8. Excel exported to `jobs_export.xlsx`
9. ResourceWarning warnings appeared from python-jobspy's unclosed sockets
10. Agent went to sleep for 120 seconds
11. User interrupted with Ctrl+C → clean shutdown

**The pipeline IS working.** The output shows:
- Jobs being saved: "💾 Saved: Lensa — AI Engineer Trainee (Remote) [jobspy]"
- Telegram messages being sent: HTTP 200 OK responses
- 78 new jobs found, 0 duplicates
- Excel exported successfully

---

## 7. COMPLETE FILE LISTING

```
job-agent/
├── .env                              (18 lines)    Secrets & user config
├── .gitignore                        (93 bytes)    Git ignore rules
├── .python-version                   (7 bytes)     Python version for pyenv
├── config.py                         (128 lines)   Central configuration
├── jobs.db                           (2.7 MB)      SQLite database
├── jobs_export.xlsx                  (12 KB)        Latest Excel export
├── main.py                           (369 lines)   Pipeline orchestrator
├── README.md                         (769 lines)   Project documentation
├── requirements.txt                  (42 lines)    Python dependencies
│
└── modules/
    ├── __init__.py                   (empty)        Package init
    ├── scraper.py.bak                (41 KB)        OLD monolithic scraper (UNUSED)
    ├── tracker.py                    (216 lines)    SQLite database layer
    ├── notifier.py                   (33 lines)     Telegram notifications
    ├── exporter.py                   (65 lines)     Excel export
    │
    ├── discovery/
    │   └── web_discovery.py          (308 lines)    DuckDuckGo domain discovery
    │
    ├── crawling/
    │   └── career_crawler.py         (243 lines)    Async career page crawler
    │
    ├── parsing/
    │   ├── greenhouse.py             (111 lines)    Greenhouse ATS scraper
    │   ├── lever.py                  (121 lines)    Lever ATS scraper
    │   ├── ashby.py                  (134 lines)    Ashby ATS scraper
    │   ├── workable.py               (117 lines)    Workable ATS scraper
    │   └── generic_html.py           (222 lines)    Generic HTML job parser
    │
    └── filtering/
        ├── rule_scoring.py           (161 lines)    Weighted keyword scoring
        ├── experience_parser.py      (89 lines)     Years-of-experience extraction
        ├── visa_filter.py            (111 lines)    Visa sponsorship scoring
        └── ollama_validator.py       (258 lines)    Local Ollama AI validation

Total: ~2,575 lines of active Python code across 14 files
```

---

## 8. HOW TO RUN

```bash
# Prerequisites
python3 --version        # Need 3.11+
ollama --version          # Need Ollama installed
ollama pull llama3        # Download LLaMA 3 model
ollama serve &            # Start Ollama server

# Install
cd job-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
# Edit .env with your Telegram token and chat ID

# Run
python main.py
# Ctrl+C to stop
```

---

## 9. WHAT "NOT WORKING PROPERLY" MIGHT MEAN

Based on the output, the pipeline IS functionally working (78 jobs saved, Telegram sent, Excel exported). The issues are:

1. **ResourceWarning spam** — Cosmetic, from python-jobspy library, not harmful
2. **Too many/too few notifications** — Tune filtering thresholds
3. **Ollama timeout** — If Ollama is slow, increase TIMEOUT in `ollama_validator.py`
4. **Irrelevant jobs getting through** — Rule scoring may need threshold increase (currently >= 2)
5. **Missing jobs** — Visa filter may be too aggressive (rejects neutral international roles)
6. **Slow cycles** — Each cycle takes 2-5 minutes due to sequential API calls + sleeps
7. **Memory growth** — Unclosed sockets from python-jobspy accumulate over hours

---

*Document generated from complete reading of all 14 source files in the job-agent project.*
