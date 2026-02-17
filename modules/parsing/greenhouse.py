# modules/parsing/greenhouse.py
"""
Greenhouse ATS job scraper.
Uses the public Greenhouse boards API.
"""

import time
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}

# Top companies using Greenhouse — AI/ML, DevTools, Fintech, Cloud, etc.
GREENHOUSE_COMPANIES = [
    # AI / LLM / ML
    "openai", "anthropic", "cohere", "mistral", "groq", "together",
    "perplexity", "huggingface", "stability", "scale", "weights-biases",
    "inflection", "adept", "runway", "jasper", "character", "pika",
    "ideogram", "elevenlabs", "deepl", "writer", "cerebras", "sambanova",
    # Dev Tools / Infra
    "vercel", "supabase", "railway", "render", "fly", "neon", "turso",
    "upstash", "clerk", "resend", "trigger", "inngest", "temporal",
    "dagster", "prefect", "gitpod", "codeium", "sourcegraph", "replit",
    "cursor", "warp", "zed", "raycast", "linear", "retool",
    "hashicorp", "pulumi", "buildkite", "circleci", "snyk",
    "launchdarkly", "flagsmith",
    # Fintech
    "stripe", "brex", "mercury", "ramp", "plaid", "unit",
    "modern-treasury", "wise", "monzo", "revolut", "coinbase",
    # Cloud / Security
    "cloudflare", "datadog", "grafana", "sentry", "wiz", "crowdstrike",
    "okta", "tailscale",
    # Data / Analytics
    "databricks", "dbt-labs", "fivetran", "airbyte", "posthog",
    "mixpanel", "clickhouse",
    # Productivity
    "notion", "figma", "miro", "loom", "coda", "linear", "clickup",
    # India
    "razorpay", "cred", "groww", "meesho", "freshworks", "postman",
    "browserstack",
]


def make_job(title, company, country, url, description, source="greenhouse"):
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


def scrape_greenhouse() -> list[dict]:
    """Scrape all Greenhouse companies for job postings."""
    log.info(f"🌿 Scraping Greenhouse ({len(GREENHOUSE_COMPANIES)} companies)...")
    jobs = []

    for company in GREENHOUSE_COMPANIES:
        try:
            r = requests.get(
                f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true",
                headers=HEADERS,
                timeout=10,
            )
            if r.status_code != 200:
                continue

            for job in r.json().get("jobs", []):
                title = job.get("title", "")
                jd_html = job.get("content", "")
                jd = BeautifulSoup(jd_html, "html.parser").get_text(
                    separator=" ", strip=True
                ) if jd_html else ""

                location = job.get("location", {}).get("name", "Remote")
                url = job.get("absolute_url", "")

                if not url:
                    continue

                jobs.append(make_job(
                    title=title,
                    company=company.replace("-", " ").title(),
                    country=location,
                    url=url,
                    description=jd[:6000],
                ))

            time.sleep(0.5)
        except Exception as e:
            log.debug(f"  Greenhouse [{company}]: {e}")

    log.info(f"  ✅ Greenhouse: {len(jobs)} raw jobs")
    return jobs
