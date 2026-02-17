# modules/discovery/web_discovery.py
"""
Global web job discovery engine.
Generates rotating search queries and discovers company career pages
using DuckDuckGo search (no API key needed).
Caches discovered domains in SQLite.
"""

import re
import time
import hashlib
import sqlite3
import logging
import random
from urllib.parse import urlparse
from datetime import datetime, timedelta

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import DB_PATH

log = logging.getLogger(__name__)

# ── Search Query Templates ────────────────────────────────────────────────────

ROLE_KEYWORDS = [
    "software engineer",
    "software developer",
    "backend engineer",
    "backend developer",
    "frontend engineer",
    "full stack developer",
    "fullstack engineer",
    "ai engineer",
    "ml engineer",
    "machine learning engineer",
    "data engineer",
    "platform engineer",
    "devops engineer",
    "cloud engineer",
    "python developer",
    "java developer",
    "react developer",
    "node.js developer",
]

LEVEL_KEYWORDS = [
    "junior",
    "graduate",
    "entry level",
    "fresher",
    "intern",
    "internship",
    "new grad",
    "trainee",
    "early career",
    "associate",
    "0-2 years",
]

COUNTRIES = [
    "India", "United Kingdom", "Germany", "Netherlands",
    "Ireland", "UAE", "Sweden", "Canada", "Australia",
    "Singapore", "Japan", "Remote",
]

SEARCH_SUFFIXES = [
    "careers",
    "apply now",
    "apply",
    "job opening",
    "hiring",
    "join us",
]

# Domains to SKIP (job boards — we want direct company sites)
SKIP_DOMAINS = {
    "linkedin.com", "indeed.com", "glassdoor.com", "monster.com",
    "ziprecruiter.com", "dice.com", "angel.co", "wellfound.com",
    "naukri.com", "simplyhired.com", "careerbuilder.com",
    "reed.co.uk", "totaljobs.com", "jobsite.co.uk", "seek.com.au",
    "stepstone.de", "xing.com", "bayt.com", "wuzzuf.net",
    "facebook.com", "twitter.com", "reddit.com", "youtube.com",
    "wikipedia.org", "github.com", "stackoverflow.com",
    "medium.com", "quora.com", "pinterest.com",
}

# Known ATS domains to flag
ATS_DOMAINS = {
    "greenhouse.io", "lever.co", "ashbyhq.com", "workable.com",
    "bamboohr.com", "jobvite.com", "icims.com", "myworkdayjobs.com",
    "smartrecruiters.com", "recruitee.com", "breezy.hr",
    "applytojob.com", "jazz.co", "taleo.net",
}


# ── SQLite Domain Cache ──────────────────────────────────────────────────────

def init_domains_table():
    """Create the discovered_domains table."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS discovered_domains (
            domain TEXT PRIMARY KEY,
            company_name TEXT DEFAULT '',
            career_url TEXT DEFAULT '',
            source_query TEXT DEFAULT '',
            is_ats INTEGER DEFAULT 0,
            last_crawled TEXT,
            job_count INTEGER DEFAULT 0,
            discovered_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def domain_exists(domain: str) -> bool:
    """Check if a domain is already in the cache."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT domain FROM discovered_domains WHERE domain = ?", (domain,))
    result = c.fetchone()
    conn.close()
    return result is not None


def save_domain(domain: str, company_name: str = "", career_url: str = "",
                source_query: str = "", is_ats: bool = False):
    """Save a discovered domain to the cache."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""
            INSERT OR IGNORE INTO discovered_domains
            (domain, company_name, career_url, source_query, is_ats)
            VALUES (?, ?, ?, ?, ?)
        """, (domain, company_name, career_url, source_query, int(is_ats)))
        conn.commit()
    except Exception as e:
        log.debug(f"Domain save error: {e}")
    finally:
        conn.close()


def get_uncrawled_domains(limit: int = 50) -> list[str]:
    """Get domains that haven't been crawled yet or were crawled >24h ago."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        SELECT domain FROM discovered_domains
        WHERE last_crawled IS NULL OR last_crawled < ?
        ORDER BY discovered_at DESC
        LIMIT ?
    """, (cutoff, limit))
    domains = [r[0] for r in c.fetchall()]
    conn.close()
    return domains


def mark_crawled(domain: str, job_count: int = 0):
    """Mark a domain as crawled."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE discovered_domains
        SET last_crawled = ?, job_count = ?
        WHERE domain = ?
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), job_count, domain))
    conn.commit()
    conn.close()


# ── Query Generator ───────────────────────────────────────────────────────────

def generate_search_queries(batch_size: int = 20) -> list[str]:
    """
    Generate a batch of rotated search queries.
    Combines role × level × country × suffix.
    """
    queries = []

    # Strategy 1: role + level + suffix
    for _ in range(batch_size // 3):
        role = random.choice(ROLE_KEYWORDS)
        level = random.choice(LEVEL_KEYWORDS)
        suffix = random.choice(SEARCH_SUFFIXES)
        queries.append(f"{level} {role} {suffix}")

    # Strategy 2: role + level + country
    for _ in range(batch_size // 3):
        role = random.choice(ROLE_KEYWORDS)
        level = random.choice(LEVEL_KEYWORDS)
        country = random.choice(COUNTRIES)
        queries.append(f"{level} {role} {country}")

    # Strategy 3: targeted queries
    targeted = [
        '"software engineer" "apply now" careers',
        '"internship" "software engineer" apply',
        '"graduate program" software engineer',
        '"entry level" backend developer hiring',
        'site:*.jobs software engineer',
        '"junior developer" "visa sponsorship"',
        '"AI ML internship" apply 2025',
        '"fresher" "software engineer" India careers',
        '"new grad" engineer hiring remote',
        '"associate engineer" careers apply',
    ]
    remaining = batch_size - len(queries)
    queries.extend(random.sample(targeted, min(remaining, len(targeted))))

    random.shuffle(queries)
    return queries[:batch_size]


# ── Domain Extraction ─────────────────────────────────────────────────────────

def extract_domain(url: str) -> str:
    """Extract clean domain from URL."""
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path.split("/")[0]
    domain = domain.replace("www.", "").lower()
    return domain


def is_valid_domain(domain: str) -> bool:
    """Check if a domain should be crawled."""
    if not domain or len(domain) < 4:
        return False
    if domain in SKIP_DOMAINS:
        return False
    if any(skip in domain for skip in SKIP_DOMAINS):
        return False
    return True


def is_ats_domain(domain: str) -> bool:
    """Check if the domain is a known ATS platform."""
    return any(ats in domain for ats in ATS_DOMAINS)


# ── Main Discovery Function ──────────────────────────────────────────────────

def discover_domains(batch_size: int = 15) -> list[str]:
    """
    Discover new company career domains using DuckDuckGo search.
    Returns list of new domains discovered.
    """
    init_domains_table()

    queries = generate_search_queries(batch_size)
    new_domains = []

    log.info(f"🌍 Web Discovery: searching with {len(queries)} queries...")

    try:
        from duckduckgo_search import DDGS
    except ImportError:
        log.warning("duckduckgo-search not installed. Run: pip install duckduckgo-search")
        return []

    ddgs = DDGS()

    for query in queries:
        try:
            results = ddgs.text(query, max_results=10)

            for result in results:
                url = result.get("href", "") or result.get("link", "")
                if not url:
                    continue

                domain = extract_domain(url)
                if not is_valid_domain(domain):
                    continue

                if not domain_exists(domain):
                    is_ats = is_ats_domain(domain)
                    company = result.get("title", "").split(" - ")[0].split(" | ")[0][:100]

                    save_domain(
                        domain=domain,
                        company_name=company,
                        career_url=url,
                        source_query=query[:200],
                        is_ats=is_ats,
                    )
                    new_domains.append(domain)
                    log.debug(f"  🆕 Discovered: {domain}")

            time.sleep(1.5)  # Be respectful to DDG

        except Exception as e:
            log.warning(f"  Search failed for '{query[:30]}': {e}")
            time.sleep(2)

    log.info(f"  🌍 Discovered {len(new_domains)} new domains")
    return new_domains


# ── Initialize on import ─────────────────────────────────────────────────────

init_domains_table()
