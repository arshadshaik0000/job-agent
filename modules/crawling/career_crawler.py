# modules/crawling/career_crawler.py
"""
Intelligent career page crawler.
Visits discovered domains, detects career pages, extracts job posting links.
Uses aiohttp for async crawling with Playwright fallback for JS-heavy sites.
"""

import re
import asyncio
import logging
from urllib.parse import urljoin, urlparse
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

# Paths that commonly lead to career/jobs pages
CAREER_PATHS = [
    "/careers",
    "/jobs",
    "/join-us",
    "/join",
    "/work-with-us",
    "/work",
    "/internships",
    "/openings",
    "/opportunities",
    "/vacancies",
    "/positions",
    "/hiring",
    "/talent",
    "/team",
    "/careers/openings",
    "/careers/jobs",
    "/about/careers",
    "/company/careers",
    "/en/careers",
]

# Link text patterns that indicate career pages
CAREER_LINK_PATTERNS = [
    re.compile(r"\bcareers?\b", re.IGNORECASE),
    re.compile(r"\bjobs?\b", re.IGNORECASE),
    re.compile(r"\bjoin\s*(us|our\s*team)\b", re.IGNORECASE),
    re.compile(r"\bwork\s*with\s*us\b", re.IGNORECASE),
    re.compile(r"\bopen\s*(positions?|roles?|ings?)\b", re.IGNORECASE),
    re.compile(r"\bhiring\b", re.IGNORECASE),
    re.compile(r"\binternships?\b", re.IGNORECASE),
]

# Patterns for job posting links
JOB_LINK_PATTERNS = [
    re.compile(r"/jobs?/\d+", re.IGNORECASE),
    re.compile(r"/openings?/", re.IGNORECASE),
    re.compile(r"/positions?/", re.IGNORECASE),
    re.compile(r"/apply/", re.IGNORECASE),
    re.compile(r"/vacancies?/", re.IGNORECASE),
    re.compile(r"greenhouse\.io/.+/jobs/\d+", re.IGNORECASE),
    re.compile(r"lever\.co/.+/[a-f0-9-]+", re.IGNORECASE),
    re.compile(r"ashbyhq\.com/.+/[a-f0-9-]+", re.IGNORECASE),
    re.compile(r"workable\.com/.+/j/", re.IGNORECASE),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

MAX_CONCURRENT = 10
TIMEOUT = 15


async def fetch_url(session: aiohttp.ClientSession, url: str) -> str | None:
    """Fetch a URL asynchronously."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                               headers=HEADERS, allow_redirects=True,
                               ssl=False) as resp:
            if resp.status != 200:
                return None
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return None
            return await resp.text(errors="replace")
    except Exception as e:
        log.debug(f"Fetch error {url[:60]}: {e}")
        return None


def find_career_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Find links that point to career/jobs pages."""
    career_urls = set()
    parsed_base = urlparse(base_url)

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        # Only follow same-domain or known ATS links
        if parsed.netloc and parsed.netloc != parsed_base.netloc:
            # Allow known ATS domains
            ats_domains = ["greenhouse.io", "lever.co", "ashbyhq.com",
                          "workable.com", "bamboohr.com", "jobvite.com"]
            if not any(d in parsed.netloc for d in ats_domains):
                continue

        # Check if the link text matches career patterns
        for pattern in CAREER_LINK_PATTERNS:
            if pattern.search(text) or pattern.search(href):
                career_urls.add(full_url)
                break

    return list(career_urls)


def find_job_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Find links that point to individual job postings."""
    job_urls = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        full_url = urljoin(base_url, href)

        for pattern in JOB_LINK_PATTERNS:
            if pattern.search(full_url):
                job_urls.add(full_url)
                break

        # Also check for apply buttons/links
        text = a.get_text(strip=True).lower()
        if "apply" in text and href and href != "#":
            job_urls.add(full_url)

    return list(job_urls)


async def detect_career_page(session: aiohttp.ClientSession,
                              domain: str) -> list[str]:
    """Try common career paths on a domain and return working URLs."""
    career_pages = []

    # Normalize domain
    if not domain.startswith("http"):
        domain = f"https://{domain}"
    domain = domain.rstrip("/")

    # Try common career paths
    tasks = []
    for path in CAREER_PATHS[:10]:  # Limit to avoid too many requests
        url = f"{domain}{path}"
        tasks.append(fetch_url(session, url))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, html in enumerate(results):
        if isinstance(html, str) and html:
            url = f"{domain}{CAREER_PATHS[i]}"
            career_pages.append(url)
            log.debug(f"  Found career page: {url}")

    # If no direct paths work, try homepage and look for career links
    if not career_pages:
        homepage_html = await fetch_url(session, domain)
        if homepage_html:
            soup = BeautifulSoup(homepage_html, "html.parser")
            career_links = find_career_links(soup, domain)
            career_pages.extend(career_links[:5])

    return career_pages


async def extract_jobs_from_page(session: aiohttp.ClientSession,
                                  career_url: str) -> list[str]:
    """Extract individual job posting URLs from a career page."""
    html = await fetch_url(session, career_url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    return find_job_links(soup, career_url)


async def crawl_domain(session: aiohttp.ClientSession,
                       domain: str) -> list[str]:
    """
    Full crawl pipeline for a single domain:
    1. Detect career pages
    2. Extract job links from those pages
    """
    career_pages = await detect_career_page(session, domain)
    if not career_pages:
        return []

    all_job_urls = []
    for page in career_pages[:5]:  # Limit pages per domain
        job_urls = await extract_jobs_from_page(session, page)
        all_job_urls.extend(job_urls)

    # Deduplicate
    return list(set(all_job_urls))


async def crawl_career_pages(domains: list[str]) -> dict[str, list[str]]:
    """
    Crawl multiple domains concurrently.
    Returns dict mapping domain -> list of job URLs.
    """
    log.info(f"🕸️  Crawling {len(domains)} domains for career pages...")

    results = {}
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def bounded_crawl(domain):
        async with semaphore:
            return domain, await crawl_domain(session, domain)

    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [bounded_crawl(d) for d in domains]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for result in completed:
            if isinstance(result, tuple):
                domain, urls = result
                if urls:
                    results[domain] = urls
                    log.info(f"  ✅ {domain}: {len(urls)} job links")
            elif isinstance(result, Exception):
                log.debug(f"  Crawl error: {result}")

    total_jobs = sum(len(v) for v in results.values())
    log.info(f"  🕸️  Total job links found: {total_jobs} across {len(results)} domains")
    return results


def run_crawler(domains: list[str]) -> dict[str, list[str]]:
    """Synchronous wrapper for the async crawler."""
    return asyncio.run(crawl_career_pages(domains))
