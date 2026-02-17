# modules/parsing/generic_html.py
"""
Generic HTML job page parser.
Extracts job title, company, location, and description from ANY career page.
Uses BeautifulSoup heuristics — no ATS-specific logic.
"""

import re
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# CSS selectors to find JD content — ordered by specificity
JD_SELECTORS = [
    ".job-description",
    ".jobDescription",
    ".job_description",
    "#job-description",
    "#jobDescription",
    ".posting-description",
    '[data-qa="job-description"]',
    '[data-testid="job-description"]',
    '[role="article"]',
    ".job-details",
    ".job-content",
    ".careers-description",
    ".position-description",
    ".vacancy-description",
    ".opening-description",
    ".role-description",
    "article.job",
    "div.job",
    "article",
    "main",
]

# Selectors for job title
TITLE_SELECTORS = [
    "h1.job-title",
    "h1.posting-headline",
    "h1.position-title",
    '[data-qa="job-title"]',
    '[data-testid="job-title"]',
    "h1",
]

# Selectors for location
LOCATION_SELECTORS = [
    ".job-location",
    ".location",
    '[data-qa="job-location"]',
    '[data-testid="location"]',
    ".posting-location",
    ".job-meta .location",
]

# Patterns for detecting "Apply" links (job posting indicators)
APPLY_PATTERNS = [
    re.compile(r"apply\s*(now|here|today)?", re.IGNORECASE),
    re.compile(r"submit\s*application", re.IGNORECASE),
]


def fetch_page(url: str, timeout: int = 12) -> BeautifulSoup | None:
    """Fetch and parse a webpage."""
    if not url or url == "nan":
        return None
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        # Remove noisy elements
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
            tag.decompose()
        return soup
    except Exception as e:
        log.debug(f"Fetch failed {url[:60]}: {e}")
        return None


def extract_title(soup: BeautifulSoup) -> str:
    """Extract job title from page using heuristics."""
    for selector in TITLE_SELECTORS:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(strip=True)
            if 5 < len(text) < 200:
                return text

    # Fallback: look for aria-label with job-related content
    for el in soup.find_all(attrs={"aria-label": True}):
        label = el.get("aria-label", "")
        if any(k in label.lower() for k in ["job", "position", "role", "title"]):
            return label[:200]

    # Fallback: page <title>
    title_tag = soup.find("title")
    if title_tag:
        text = title_tag.get_text(strip=True)
        # Try to extract role from "Role - Company" patterns
        parts = re.split(r"\s*[|–—-]\s*", text)
        if parts:
            return parts[0].strip()[:200]

    return ""


def extract_company(soup: BeautifulSoup, url: str) -> str:
    """Extract company name from page or URL."""
    # Try meta/OG tags
    for tag in soup.find_all("meta", attrs={"property": "og:site_name"}):
        return tag.get("content", "")[:100]

    # Try common selectors
    for selector in [".company-name", ".employer", '[data-qa="company"]']:
        el = soup.select_one(selector)
        if el:
            return el.get_text(strip=True)[:100]

    # Fallback: domain name
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "").split(".")[0]
    return domain.replace("-", " ").title()


def extract_location(soup: BeautifulSoup) -> str:
    """Extract job location from page."""
    for selector in LOCATION_SELECTORS:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(strip=True)
            if 2 < len(text) < 150:
                return text

    # Look for location icon patterns (📍 or similar)
    for el in soup.find_all(string=re.compile(r"📍|location:", re.IGNORECASE)):
        parent = el.parent
        if parent:
            text = parent.get_text(strip=True)
            loc = re.sub(r"^(📍|location:)\s*", "", text, flags=re.IGNORECASE)
            if 2 < len(loc) < 150:
                return loc

    return "Unknown"


def extract_description(soup: BeautifulSoup) -> str:
    """Extract job description from page."""
    for selector in JD_SELECTORS:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(separator=" ", strip=True)
            if len(text) > 200:
                return text[:6000]

    # Fallback: full body text
    body = soup.find("body")
    if body:
        return body.get_text(separator=" ", strip=True)[:6000]

    return ""


def has_apply_button(soup: BeautifulSoup) -> bool:
    """Check if the page has an apply button — indicating it's a job posting."""
    for el in soup.find_all(["a", "button"]):
        text = el.get_text(strip=True)
        for pattern in APPLY_PATTERNS:
            if pattern.search(text):
                return True
    return False


def parse_job_page(url: str) -> dict | None:
    """
    Parse any job page and extract structured data.
    Returns dict or None if parsing fails.
    """
    soup = fetch_page(url)
    if not soup:
        return None

    title = extract_title(soup)
    if not title:
        return None

    description = extract_description(soup)
    if len(description) < 100:
        return None

    company = extract_company(soup, url)
    location = extract_location(soup)

    return {
        "job_title": title,
        "company": company,
        "country": location,
        "job_url": url,
        "jd_content": description,
        "source": "web_discovery",
        "visa_sponsorship": "unknown",
        "has_apply": has_apply_button(soup),
    }


def fetch_full_jd(url: str, timeout: int = 12) -> str:
    """Fetch just the JD text from a URL (used to enrich short descriptions)."""
    soup = fetch_page(url, timeout)
    if not soup:
        return ""
    return extract_description(soup)
