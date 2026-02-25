# config.py — Job Discovery Agent Configuration
import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================================
# API KEYS
# ==========================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ==========================================================
# DATABASE
# ==========================================================
DB_PATH = "jobs.db"

# ==========================================================
# SEARCH TERMS (aggressive keyword list)
# ==========================================================
SEARCH_TERMS = [
    "graduate software engineer",
    "junior software engineer",
    "entry level software engineer",
    "junior backend engineer",
    "junior full stack engineer",
    "ai engineer junior",
    "associate software engineer",
    "software engineer new grad",
    "junior platform engineer",
    "ml engineer entry level",
]

# ==========================================================
# TARGET REGIONS
# ==========================================================
SEARCH_LOCATIONS = [
    "India",
    "United Kingdom",
    "Germany",
    "Netherlands",
    "Ireland",
    "UAE",
    "Sweden",
    "Poland",
    "Spain",
    "Remote",
]

# ==========================================================
# TITLE FILTERS
# ==========================================================
REJECT_TITLE_KEYWORDS = [
    "senior", "staff", "principal", "lead",
    "manager", "director", "architect", "vp",
    "head of", "chief",
]

# ==========================================================
# VISA / SPONSORSHIP KEYWORDS
# ==========================================================
SPONSORSHIP_KEYWORDS = [
    "visa sponsorship", "sponsorship available",
    "relocation support", "work visa", "sponsor visa",
    "relocation package", "relocation assistance",
    "international candidates welcome", "we sponsor",
]

# ==========================================================
# LANGUAGE REJECT KEYWORDS
# ==========================================================
NON_ENGLISH_KEYWORDS = [
    "german required", "japanese required",
    "mandarin required", "french required",
    "fluent german", "native japanese",
    "dutch required",
]

# ==========================================================
# STARTUP ATS BOARD SLUGS (Greenhouse + Lever)
# ==========================================================
GREENHOUSE_COMPANIES = [
    "stripe", "cloudflare", "datadog", "notion",
    "figma", "plaid", "coinbase", "canonical",
    "elastic", "snyk", "hashicorp", "mongodb",
    "cockroachlabs", "squarespace", "airtable",
    "gitlab", "hubspot", "twilio", "discord",
    "reddit", "brex", "ramp", "affirm",
    "instacart", "doordash",
]

LEVER_COMPANIES = [
    "netlify", "postman", "webflow",
]