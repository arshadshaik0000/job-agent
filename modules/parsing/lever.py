# modules/parsing/lever.py
"""
Lever ATS job scraper.
Uses the public Lever postings API.
"""

import time
import logging
import requests
from datetime import datetime

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}

LEVER_COMPANIES = [
    # Big Tech Adjacent
    "netflix", "dropbox", "atlassian", "zendesk", "hubspot",
    "servicenow", "splunk", "elastic", "mongodb", "redis",
    "cockroachdb", "yugabyte",
    # Fintech
    "affirm", "klarna", "chime", "current", "greenlight", "step",
    # Dev / Cloud
    "digitalocean", "airtable", "webflow", "bubble", "retool",
    # Data
    "snowflake", "looker", "metabase", "dune",
    # Security
    "expel", "vectra", "abnormal", "proofpoint",
    # Logistics
    "flexport", "samsara", "motive",
    # HR
    "bamboohr", "gusto", "justworks", "rippling",
    # Media / Travel / Consumer
    "substack", "medium", "airbnb", "hopper",
    "duolingo", "coursera", "masterclass", "brilliant",
    # Europe
    "personio", "pleo", "spendesk", "typeform",
    # Israel
    "wix", "monday", "fiverr", "taboola",
    # India
    "razorpay", "freshworks", "postman",
    # APAC
    "grab", "sea", "carousell",
    # Africa
    "andela", "flutterwave", "paystack",
]


def make_job(title, company, country, url, description, source="lever"):
    return {
        "job_title": title.strip(),
        "company": company.strip(),
        "country": country.strip(),
        "job_url": url.strip(),
        "jd_content": description,
        "source": source,
        "visa_sponsorship": "unknown",
        "date_found": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "found",
        "hr_score": 0,
        "notes": "",
        "resume_version": "",
        "skills_emphasized": "",
    }


def scrape_lever() -> list[dict]:
    """Scrape all Lever companies for job postings."""
    log.info(f"⚙️  Scraping Lever ({len(LEVER_COMPANIES)} companies)...")
    jobs = []

    for company in LEVER_COMPANIES:
        try:
            r = requests.get(
                f"https://api.lever.co/v0/postings/{company}?mode=json",
                headers=HEADERS,
                timeout=10,
            )
            if r.status_code != 200:
                continue

            for job in r.json():
                title = job.get("text", "")
                url = job.get("hostedUrl", "")

                if not url:
                    continue

                # Extract description from descriptionBody blocks
                desc_parts = []
                body = job.get("descriptionBody", {})
                if isinstance(body, dict):
                    for block in body.get("body", []):
                        if isinstance(block, dict):
                            desc_parts.append(block.get("text", ""))
                desc = " ".join(desc_parts)

                # Also try descriptionPlain or description
                if not desc:
                    desc = job.get("descriptionPlain", "") or job.get("description", "")

                location = job.get("categories", {}).get("location", "Remote")

                jobs.append(make_job(
                    title=title,
                    company=company.replace("-", " ").title(),
                    country=location,
                    url=url,
                    description=desc[:6000],
                ))

            time.sleep(0.5)
        except Exception as e:
            log.debug(f"  Lever [{company}]: {e}")

    log.info(f"  ✅ Lever: {len(jobs)} raw jobs")
    return jobs
