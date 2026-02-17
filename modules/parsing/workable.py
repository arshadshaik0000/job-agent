# modules/parsing/workable.py
"""
Workable ATS job scraper.
Uses the public Workable jobs API.
"""

import time
import logging
import requests
from datetime import datetime

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Content-Type": "application/json",
}

WORKABLE_COMPANIES = [
    # EU Startups
    "taxfix", "revolut", "n26", "trade-republic", "sumup",
    "personio", "contentful", "ecosia", "babbel",
    "raisin", "solarisbank", "pleo", "leapsome",
    "factorial", "typeform", "payhawk", "spendesk",
    # UK
    "monzo", "starling", "wise", "oaknorth", "iwoca",
    "truelayer", "form3", "modulr", "checkout", "primer", "paddle",
    # Nordic
    "klarna", "spotify", "king", "kahoot", "whereby", "visma",
    # Eastern Europe
    "grammarly", "gitlab", "preply", "playtika",
    # MENA
    "careem", "noon", "talabat",
    # APAC
    "grab", "sea", "shopee", "tokopedia", "traveloka", "gojek",
    # LATAM
    "nubank", "mercadolibre", "rappi", "ifood",
    # Africa
    "andela", "flutterwave", "paystack", "kuda",
    # Japan
    "mercari", "freee", "moneyforward", "smartnews",
    # Israel
    "wix", "monday", "fiverr", "taboola",
    # India
    "razorpay", "cred", "groww", "meesho", "freshworks",
    "zoho", "chargebee", "postman", "browserstack",
]


def make_job(title, company, country, url, description, source="workable"):
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


def scrape_workable() -> list[dict]:
    """Scrape all Workable companies for job postings."""
    log.info(f"🔧 Scraping Workable ({len(WORKABLE_COMPANIES)} companies)...")
    jobs = []

    for company in WORKABLE_COMPANIES:
        try:
            r = requests.post(
                f"https://apply.workable.com/api/v3/accounts/{company}/jobs",
                json={
                    "query": "",
                    "location": [],
                    "department": [],
                    "worktype": [],
                    "remote": [],
                },
                headers=HEADERS,
                timeout=10,
            )
            if r.status_code != 200:
                continue

            for job in r.json().get("results", []):
                title = job.get("title", "")
                shortcode = job.get("shortcode", "")

                if not shortcode:
                    continue

                job_url = f"https://apply.workable.com/{company}/j/{shortcode}/"
                location = job.get("location", {})
                country = location.get("country", "")
                city = location.get("city", "")
                loc_str = f"{city}, {country}".strip(", ") if city else country or "Remote"

                jobs.append(make_job(
                    title=title,
                    company=company.replace("-", " ").title(),
                    country=loc_str,
                    url=job_url,
                    description=job.get("description", "")[:6000],
                ))

            time.sleep(0.5)
        except Exception as e:
            log.debug(f"  Workable [{company}]: {e}")

    log.info(f"  ✅ Workable: {len(jobs)} raw jobs")
    return jobs
