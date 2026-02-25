<p align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=700&size=40&pause=1000&color=6C63FF&center=true&vCenter=true&random=false&width=800&height=80&lines=Job+Discovery+Agent+%F0%9F%94%8D;Autonomous+Job+Hunter+%F0%9F%A4%96;Multi-Source+Scraper+%F0%9F%8C%90" alt="Typing SVG" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white" />
  <img src="https://img.shields.io/badge/Telegram-Notifications-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" />
  <img src="https://img.shields.io/badge/Ollama-AI%20Validation-FF6F00?style=for-the-badge&logo=ollama&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" />
</p>

<p align="center">
  <b>An aggressive, fully autonomous Python agent that discovers entry-level & junior software engineering jobs across 10+ countries from 7+ sources — filters, scores, validates with local AI, stores in SQLite, and sends real-time Telegram alerts.</b>
</p>

---

## 🧠 What Is This?

**Job Discovery Agent** is a self-running Python pipeline that hunts for junior/entry-level software engineering opportunities 24/7. It doesn't apply or send resumes — it focuses purely on **discovery, filtering, and notification** so you never miss a relevant opening.

Every **60 minutes**, it:
1. 🔎 **Scrapes** jobs from LinkedIn, Indeed, Glassdoor, Greenhouse, Lever, Ashby, and Workable
2. 🌐 **Discovers** new companies via DuckDuckGo search and crawls their career pages
3. 🧪 **Filters** using a 4-layer intelligent pipeline (visa, rules, experience, AI)
4. 💾 **Saves** to a local SQLite database (deduplication by URL)
5. 📲 **Notifies** you instantly via Telegram with a formatted job card

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        main.py (Scheduler)                      │
│                     APScheduler — 60 min loop                   │
├─────────────┬─────────────┬─────────────┬───────────────────────┤
│  SCRAPING   │  FILTERING  │   STORAGE   │    NOTIFICATIONS      │
├─────────────┼─────────────┼─────────────┼───────────────────────┤
│ JobSpy      │ Visa Filter │ SQLite DB   │ Telegram Bot API      │
│ (LinkedIn,  │ Rule Scoring│ (tracker.py)│ (notifier.py)         │
│  Indeed,    │ Exp. Parser │             │                       │
│  Glassdoor) │ Ollama AI   │             │ Excel Exporter        │
│ Greenhouse  │             │             │ (exporter.py)         │
│ Lever       │             │             │                       │
│ Ashby       │             │             │                       │
│ Workable    │             │             │                       │
│ Web Crawler │             │             │                       │
├─────────────┴─────────────┴─────────────┴───────────────────────┤
│                       config.py (All settings)                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📡 Data Sources (7+)

| Source | Method | Coverage |
|--------|--------|----------|
| **LinkedIn** | JobSpy library | Global |
| **Indeed** | JobSpy library | Global |
| **Glassdoor** | JobSpy library | Global |
| **Greenhouse** | REST API (`boards-api.greenhouse.io`) | 70+ top startups (OpenAI, Stripe, Cloudflare, etc.) |
| **Lever** | REST API (`api.lever.co`) | 50+ companies (Netflix, Airbnb, Dropbox, etc.) |
| **Ashby** | GraphQL API (`jobs.ashbyhq.com`) | 60+ companies (Anthropic, Vercel, Supabase, etc.) |
| **Workable** | REST API (`apply.workable.com`) | 50+ companies (Revolut, Monzo, Spotify, etc.) |
| **Web Discovery** | DuckDuckGo → Career page crawling | Dynamic — discovers new companies automatically |

### 🎯 Target Companies (200+)

Covers top-tier companies across categories:

- **AI/ML**: OpenAI, Anthropic, Cohere, Mistral, Groq, Perplexity, Hugging Face, Stability AI, ElevenLabs
- **Dev Tools**: Vercel, Supabase, Railway, Render, Cursor, Replit, Linear, Retool, GitPod
- **Fintech**: Stripe, Brex, Mercury, Ramp, Plaid, Wise, Monzo, Revolut, Coinbase
- **Cloud/Security**: Cloudflare, Datadog, Grafana, Sentry, Wiz, Tailscale
- **India**: Razorpay, CRED, Groww, Meesho, Freshworks, Postman, BrowserStack, Zoho

---

## 🧪 4-Layer Intelligent Filtering

Every job passes through **four sequential filters** before being saved:

### Layer 1 — Visa & Sponsorship Filter
```
🇮🇳 India jobs         → auto-pass (no sponsorship needed)
🌍 Remote internships  → auto-pass
🌐 International jobs  → scored on 30+ sponsorship keywords
❌ "No sponsorship"    → rejected
```

### Layer 2 — Rule-Based Scoring
```
✅ Title signals:   "intern" (+4), "junior" (+3), "graduate" (+3), "associate" (+2)
❌ Title signals:   "senior" (-6), "staff" (-6), "lead" (-6), "director" (-6)
✅ JD signals:      "0-2 years" (+2), "new grad" (+2), "internship" (+3)
❌ JD signals:      "5+ years" (-4), "10+ years" (-5), "managed a team" (-4)
🎯 Accept threshold: score ≥ 2
```

### Layer 3 — Experience Parser
```
📄 Regex extraction of "X+ years" / "X-Y years" / "minimum X years"
✅ Internship titles → auto-pass
❌ Requires 3+ years → rejected
✅ 0-2 years or no mention → passed
```

### Layer 4 — Ollama AI Validation (Optional)
```
🤖 Local LLM (qwen2.5:7b-instruct) via Ollama
📝 Structured JSON response: { decision, confidence, reason }
💾 Results cached in SQLite to avoid re-validation
🔄 3 retries with exponential backoff
```

---

## 🌍 Target Regions

| Region | Countries |
|--------|-----------|
| **South Asia** | India |
| **Europe** | United Kingdom, Germany, Netherlands, Ireland, Sweden, Poland, Spain |
| **Middle East** | UAE (Dubai, Abu Dhabi) |
| **Americas** | USA, Canada |
| **APAC** | Singapore, Australia, Japan |
| **Other** | Remote / Global |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- A Telegram bot token ([create one via BotFather](https://t.me/BotFather))
- (Optional) [Ollama](https://ollama.com) for AI validation layer

### 1. Clone & Setup

```bash
git clone https://github.com/arshadshaik0000/job-agent.git
cd job-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# Telegram Bot
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Your Info (for future resume features)
APPLICANT_NAME=Your Name
APPLICANT_EMAIL=your@email.com
APPLICANT_PHONE=1234567890
APPLICANT_LINKEDIN=https://linkedin.com/in/yourprofile
APPLICANT_GITHUB=https://github.com/yourusername
APPLICANT_LOCATION=Your City, Country
```

### 3. Run

```bash
python main.py
```

You'll see:
```
🚀 Aggressive Job Discovery Agent Started
📡 Sources: LinkedIn, Indeed, Glassdoor, Greenhouse, Lever
⏱  Interval: every 60 minutes
🌍 Regions: India, UK, Germany, Netherlands, Ireland, UAE, Sweden, Poland, Spain, Remote

✅ Database initialized!

🔎 Aggressive scraping started...
📡 Source 1: JobSpy (LinkedIn / Indeed / Glassdoor)
  ✅ India | 'junior software engineer': 12 jobs
  ✅ United Kingdom | 'graduate software engineer': 8 jobs
🌱 Source 2: Greenhouse startup boards
  🌱 Greenhouse | stripe: 45 jobs
🔧 Source 3: Lever startup boards
  🔧 Lever | netflix: 23 jobs

📊 Scan Summary:
  ✅ New jobs sent:   34
  🔍 Filtered out:   128
  🔁 Duplicates:     17
```

---

## 📂 Project Structure

```
job-agent/
├── main.py                          # Entry point — scheduler + top-level filters
├── config.py                        # All configuration (search terms, regions, API keys)
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables (git-ignored)
├── jobs.db                          # SQLite database (git-ignored)
├── jobs_export.xlsx                 # Excel export (git-ignored)
│
└── modules/
    ├── scraper.py                   # Multi-source aggregator (JobSpy + Greenhouse + Lever)
    ├── tracker.py                   # SQLite database operations (init, save, deduplicate)
    ├── notifier.py                  # Telegram bot notifications
    ├── exporter.py                  # Excel export (openpyxl)
    │
    ├── crawling/
    │   └── career_crawler.py        # Async career page crawler (aiohttp, 10 concurrent)
    │
    ├── discovery/
    │   └── web_discovery.py         # DuckDuckGo domain discovery + SQLite cache
    │
    ├── filtering/
    │   ├── visa_filter.py           # Visa/sponsorship scoring (30+ keywords)
    │   ├── rule_scoring.py          # Weighted title + JD scoring system
    │   ├── experience_parser.py     # Years-of-experience regex extraction
    │   └── ollama_validator.py      # Local AI validation via Ollama (cached)
    │
    └── parsing/
        ├── greenhouse.py            # Greenhouse ATS parser (70+ companies)
        ├── lever.py                 # Lever ATS parser (50+ companies)
        ├── ashby.py                 # Ashby GraphQL parser (60+ companies)
        ├── workable.py              # Workable API parser (50+ companies)
        └── generic_html.py          # Universal HTML job page parser (heuristic)
```

---

## 💾 Database Schema

```sql
CREATE TABLE jobs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    job_title         TEXT,
    company           TEXT,
    country           TEXT,
    job_url           TEXT UNIQUE,    -- deduplication key
    visa_sponsorship  TEXT,           -- 'sponsored' | 'not_required' | 'unknown'
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

---

## 📲 Telegram Notifications

Each discovered job is sent as a formatted Telegram message:

```
🚀 New Job Found!

🏢 Company: Stripe
💼 Role: Junior Software Engineer
🌍 Location: Bangalore, India
🗺 Country: India
✈️ Visa: Not Required (India) 🇮🇳
📅 Posted: 2026-02-24
📡 Source: Greenhouse
🔗 Apply Here
```

At the end of every scan cycle, a summary is also sent:
```
📊 Scan Complete — 2026-02-25 16:30:00
✅ New jobs: 34
🔍 Filtered: 128
🔁 Duplicates: 17
```

---

## ⚙️ Configuration

All settings are centralized in `config.py`:

| Setting | Description |
|---------|-------------|
| `SEARCH_TERMS` | 10 keyword combinations (e.g., "junior software engineer", "ai engineer junior") |
| `SEARCH_LOCATIONS` | 10 target regions (India, UK, Germany, Netherlands, etc.) |
| `REJECT_TITLE_KEYWORDS` | Titles to skip (senior, staff, lead, director, etc.) |
| `SPONSORSHIP_KEYWORDS` | 9 visa/sponsorship phrases to look for |
| `NON_ENGLISH_KEYWORDS` | Language requirements that cause rejection |
| `GREENHOUSE_COMPANIES` | 25 companies to scrape from Greenhouse |
| `LEVER_COMPANIES` | 3 companies to scrape from Lever |

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `python-jobspy` | Scrape LinkedIn, Indeed, Glassdoor |
| `python-telegram-bot` | Send Telegram notifications |
| `APScheduler` | Periodic job scheduling (every 60 min) |
| `python-dotenv` | Load `.env` configuration |
| `pandas` | DataFrame manipulation for JobSpy results |
| `requests` | HTTP requests to ATS APIs |
| `beautifulsoup4` | HTML parsing for job descriptions |
| `aiohttp` | Async HTTP for career page crawling |
| `openpyxl` | Excel export |

---

## 🔮 Roadmap

- [ ] Auto-apply to selected jobs (resume submission)
- [ ] AI-powered resume tailoring per job description
- [ ] Dashboard UI for reviewing discovered jobs
- [ ] Email digest (daily/weekly summary)
- [ ] Priority scoring based on company tier
- [ ] Slack integration alongside Telegram

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=600&size=22&pause=1000&color=6C63FF&center=true&vCenter=true&random=false&width=600&height=50&lines=Built+with+%E2%9D%A4%EF%B8%8F+by+Arshad+Uzzama+Shaik;Never+miss+a+job+again+%F0%9F%9A%80" alt="Footer" />
</p>
