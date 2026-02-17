# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ── Ollama (Local AI) ────────────────────────────────────────────────────────

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

# ── Applicant Info ────────────────────────────────────────────────────────────

APPLICANT = {
    "name": os.getenv("APPLICANT_NAME"),
    "email": os.getenv("APPLICANT_EMAIL"),
    "phone": os.getenv("APPLICANT_PHONE"),
    "linkedin": os.getenv("APPLICANT_LINKEDIN"),
    "github": os.getenv("APPLICANT_GITHUB"),
    "location": os.getenv("APPLICANT_LOCATION"),
    "graduation_year": 2025,
    "degree": "B.Tech CSE — AI & ML",
}

# ── Job Search Settings ──────────────────────────────────────────────────────

TARGET_ROLES = [
    "Software Engineer",
    "Software Developer",
    "Backend Engineer",
    "Backend Developer",
    "Frontend Engineer",
    "Full Stack Developer",
    "AI Engineer",
    "ML Engineer",
    "Data Engineer",
    "Platform Engineer",
    "DevOps Engineer",
    "Cloud Engineer",
    "Python Developer",
    "Java Developer",
]

TARGET_LEVELS = [
    "Intern", "Internship", "Junior", "Graduate",
    "Entry Level", "Fresher", "New Grad", "Trainee",
    "Associate", "Early Career", "Apprentice",
]

TECH_STACK = [
    "python", "java", "spring boot", "react", "aws",
    "docker", "kubernetes", "node.js", "fastapi", "django",
    "postgres", "postgresql", "rest api", "microservices",
    "ai", "ml", "machine learning", "data pipeline",
    "backend", "full stack", "devops", "cloud",
]

# ── Filtering Thresholds ─────────────────────────────────────────────────────

MIN_RULE_SCORE = 2          # Minimum score from rule_scoring to pass
MAX_EXPERIENCE_YEARS = 3    # Reject if JD requires >= this many years
MIN_HR_SCORE = int(os.getenv("MIN_HR_SCORE", 70))
DAILY_TARGET = int(os.getenv("DAILY_TARGET", 250))

# ── Crawler Settings ─────────────────────────────────────────────────────────

CRAWL_MAX_DOMAINS = 30      # Max domains to crawl per cycle
CRAWL_TIMEOUT = 15           # Seconds per request
CRAWL_CONCURRENCY = 10       # Max concurrent async requests
DISCOVERY_BATCH_SIZE = 15    # DDG queries per discovery cycle

# ── Scan Settings ─────────────────────────────────────────────────────────────

SCAN_INTERVAL_SECONDS = 120  # Time between scan cycles

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE_RESUME_PATH = "resumes/base/base_resume.tex"
RESUMES_DIR = "resumes"
LOGS_DIR = "logs"
DB_PATH = "jobs.db"

# ── JobSpy Search Queries ─────────────────────────────────────────────────────

JOBSPY_SEARCHES = [
    # India
    {"term": "graduate software engineer", "location": "India", "country": "India"},
    {"term": "junior backend engineer", "location": "India", "country": "India"},
    {"term": "software engineer intern", "location": "India", "country": "India"},
    {"term": "entry level software engineer", "location": "India", "country": "India"},
    {"term": "software engineering internship", "location": "India", "country": "India"},
    {"term": "junior python developer", "location": "India", "country": "India"},
    {"term": "AI ML intern", "location": "India", "country": "India"},
    {"term": "software engineer", "location": "Bangalore", "country": "India"},
    {"term": "software engineer", "location": "Hyderabad", "country": "India"},
    {"term": "software engineer", "location": "Pune", "country": "India"},
    # UK
    {"term": "graduate software engineer", "location": "United Kingdom", "country": "United Kingdom"},
    {"term": "junior developer sponsorship", "location": "London", "country": "United Kingdom"},
    {"term": "software engineer internship", "location": "United Kingdom", "country": "United Kingdom"},
    # Germany
    {"term": "junior software engineer", "location": "Berlin", "country": "Germany"},
    {"term": "software engineering intern", "location": "Munich", "country": "Germany"},
    # Netherlands
    {"term": "junior software engineer", "location": "Amsterdam", "country": "Netherlands"},
    # Ireland
    {"term": "graduate software engineer", "location": "Dublin", "country": "Ireland"},
    # UAE
    {"term": "junior software engineer", "location": "Dubai", "country": "UAE"},
    # Canada
    {"term": "junior software engineer", "location": "Toronto", "country": "Canada"},
    # Australia
    {"term": "graduate software engineer", "location": "Sydney", "country": "Australia"},
    # Singapore
    {"term": "junior software engineer", "location": "Singapore", "country": "Singapore"},
    # Japan
    {"term": "software engineer english", "location": "Tokyo", "country": "Japan"},
    # Remote
    {"term": "remote junior software engineer", "location": "Remote", "country": "Remote"},
    {"term": "remote software engineering internship", "location": "Remote", "country": "Remote"},
    {"term": "remote graduate engineer", "location": "Remote", "country": "Remote"},
]