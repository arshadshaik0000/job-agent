# modules/parsing/ashby.py
"""
Ashby ATS job scraper.
Uses the public Ashby GraphQL API.
"""

import time
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Content-Type": "application/json",
}

ASHBY_COMPANIES = [
    # AI/ML
    "openai", "anthropic", "mistral", "cohere", "perplexity",
    "elevenlabs", "runway", "pika", "ideogram", "stability",
    # Dev Tools
    "replit", "cursor", "vercel", "supabase", "railway",
    "linear", "retool", "render", "fly", "planetscale",
    "turso", "neon", "upstash", "clerk", "resend",
    "trigger", "inngest", "dagster", "prefect", "temporal",
    # OSS / Indie
    "posthog", "cal", "dub", "plane", "appflowy", "logseq",
    "chatwoot", "typebot", "activepieces", "windmill", "n8n",
    # Fintech
    "brex", "mercury", "ramp", "unit", "lithic",
    "modern-treasury", "check", "column", "stripe",
    # Data
    "airbyte", "hightouch", "census", "rudderstack",
    "fivetran", "dbt-labs", "lightdash", "hex",
    # Security
    "wiz", "snyk", "semgrep",
    # HR
    "rippling", "deel", "remote", "oyster", "hibob",
    # APAC/Japan
    "mercari", "freee", "grab", "sea", "carousell",
]

GRAPHQL_QUERY = """query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
    jobBoard: jobBoardWithTeams(organizationHostedJobsPageName: $organizationHostedJobsPageName) {
        jobPostings {
            id
            title
            locationName
            jobPostingState
            descriptionHtml
            externalLink
        }
    }
}"""


def make_job(title, company, country, url, description, source="ashby"):
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


def scrape_ashby() -> list[dict]:
    """Scrape all Ashby companies for job postings."""
    log.info(f"🔷 Scraping Ashby ({len(ASHBY_COMPANIES)} companies)...")
    jobs = []

    for company in ASHBY_COMPANIES:
        try:
            payload = {
                "operationName": "ApiJobBoardWithTeams",
                "variables": {"organizationHostedJobsPageName": company},
                "query": GRAPHQL_QUERY,
            }
            r = requests.post(
                "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams",
                json=payload,
                headers=HEADERS,
                timeout=10,
            )
            if r.status_code != 200:
                continue

            postings = (
                r.json().get("data", {}).get("jobBoard", {}).get("jobPostings", [])
            )

            for job in postings:
                title = job.get("title", "")

                if job.get("jobPostingState") != "Listed":
                    continue

                jd_html = job.get("descriptionHtml", "")
                jd = BeautifulSoup(jd_html, "html.parser").get_text(
                    separator=" ", strip=True
                ) if jd_html else ""

                job_url = (
                    job.get("externalLink")
                    or f"https://jobs.ashbyhq.com/{company}/{job.get('id')}"
                )
                location = job.get("locationName", "Remote")

                jobs.append(make_job(
                    title=title,
                    company=company.replace("-", " ").title(),
                    country=location,
                    url=job_url,
                    description=jd[:6000],
                ))

            time.sleep(0.5)
        except Exception as e:
            log.debug(f"  Ashby [{company}]: {e}")

    log.info(f"  ✅ Ashby: {len(jobs)} raw jobs")
    return jobs
