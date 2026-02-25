"""
scraper.py — Aggressive Multi-Source Job Scraper
Sources: LinkedIn, Indeed, Glassdoor (via jobspy) + Greenhouse + Lever startup boards
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import requests
from bs4 import BeautifulSoup
from jobspy import scrape_jobs

from config import (
    SEARCH_TERMS, SEARCH_LOCATIONS,
    GREENHOUSE_COMPANIES, LEVER_COMPANIES,
)


# ==========================================================
# COUNTRY EXTRACTION (from location strings)
# ==========================================================
CITY_TO_COUNTRY = {
    "india": "India", "bangalore": "India", "bengaluru": "India",
    "hyderabad": "India", "mumbai": "India", "delhi": "India",
    "pune": "India", "chennai": "India", "kolkata": "India",
    "noida": "India", "gurgaon": "India", "gurugram": "India",
    "united kingdom": "United Kingdom", "london": "United Kingdom",
    "uk": "United Kingdom", "manchester": "United Kingdom",
    "edinburgh": "United Kingdom", "cambridge": "United Kingdom",
    "germany": "Germany", "berlin": "Germany", "munich": "Germany",
    "hamburg": "Germany", "frankfurt": "Germany",
    "netherlands": "Netherlands", "amsterdam": "Netherlands",
    "ireland": "Ireland", "dublin": "Ireland",
    "uae": "UAE", "dubai": "UAE", "abu dhabi": "UAE",
    "sweden": "Sweden", "stockholm": "Sweden",
    "poland": "Poland", "warsaw": "Poland", "krakow": "Poland",
    "spain": "Spain", "madrid": "Spain", "barcelona": "Spain",
    "usa": "USA", "united states": "USA", "new york": "USA",
    "san francisco": "USA", "seattle": "USA", "austin": "USA",
    "canada": "Canada", "toronto": "Canada", "vancouver": "Canada",
    "singapore": "Singapore",
    "remote": "Remote",
}


def extract_country(location_str):
    """Extract country from a free-text location string."""
    loc = (location_str or "").lower()
    for keyword, country in CITY_TO_COUNTRY.items():
        if keyword in loc:
            return country
    return "International"


# ==========================================================
# SOURCE 1: JOBSPY (LinkedIn / Indeed / Glassdoor)
# ==========================================================
def search_jobspy():
    """Scrape LinkedIn, Indeed, Glassdoor using jobspy library."""
    jobs = []

    for location in SEARCH_LOCATIONS:
        for term in SEARCH_TERMS:
            try:
                df = scrape_jobs(
                    site_name=["linkedin", "indeed", "glassdoor"],
                    search_term=term,
                    location=location,
                    results_wanted=15,
                    hours_old=72,
                    linkedin_fetch_description=True,
                )

                if df.empty:
                    continue

                count = 0
                for _, row in df.iterrows():
                    url = str(row.get("job_url", ""))
                    if not url or url == "nan":
                        continue
                    date_posted = str(row.get("date_posted", ""))
                    if date_posted == "nan" or date_posted == "NaT":
                        date_posted = ""
                    jobs.append({
                        "job_title":    str(row.get("title", "")),
                        "company":      str(row.get("company", "")),
                        "location":     str(row.get("location", "")),
                        "country":      location,
                        "job_url":      url,
                        "jd_content":   str(row.get("description", "")),
                        "source":       str(row.get("site", "jobspy")),
                        "date_posted":  date_posted,
                    })
                    count += 1

                if count:
                    print(f"  ✅ {location} | '{term}': {count} jobs")

            except Exception as e:
                print(f"  ⚠️ {location} | '{term}': {e}")

            time.sleep(2)

    return jobs


# ==========================================================
# SOURCE 2: GREENHOUSE STARTUP BOARDS
# ==========================================================
def search_greenhouse():
    """Scrape Greenhouse JSON API for each company board."""
    jobs = []

    for company in GREENHOUSE_COMPANIES:
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                continue

            data = resp.json()
            count = 0

            for item in data.get("jobs", []):
                title    = item.get("title", "")
                location = item.get("location", {}).get("name", "")
                job_url  = item.get("absolute_url", "")
                html     = item.get("content", "")
                updated  = item.get("updated_at", "")

                if not job_url:
                    continue

                # Parse date
                date_posted = ""
                if updated:
                    try:
                        date_posted = updated[:10]  # "2025-02-14T.." → "2025-02-14"
                    except:
                        pass

                description = ""
                if html:
                    try:
                        description = BeautifulSoup(html, "html.parser").get_text(separator=" ")
                    except:
                        description = html

                jobs.append({
                    "job_title":    title,
                    "company":      company.replace("-", " ").title(),
                    "location":     location,
                    "country":      extract_country(location),
                    "job_url":      job_url,
                    "jd_content":   description,
                    "source":       "greenhouse",
                    "date_posted":  date_posted,
                })
                count += 1

            if count:
                print(f"  🌱 Greenhouse | {company}: {count} jobs")

        except Exception:
            continue

        time.sleep(1)

    return jobs


# ==========================================================
# SOURCE 3: LEVER STARTUP BOARDS
# ==========================================================
def search_lever():
    """Scrape Lever JSON API for each company board."""
    jobs = []

    for company in LEVER_COMPANIES:
        try:
            url = f"https://api.lever.co/v0/postings/{company}?mode=json"
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                continue

            data = resp.json()
            count = 0

            for posting in data:
                title    = posting.get("text", "")
                location = posting.get("categories", {}).get("location", "")
                job_url  = posting.get("hostedUrl", "")
                content  = posting.get("descriptionPlain", "")
                created  = posting.get("createdAt", 0)

                if not job_url:
                    continue

                # Lever uses epoch ms
                date_posted = ""
                if created:
                    try:
                        from datetime import datetime as dt
                        date_posted = dt.fromtimestamp(created / 1000).strftime("%Y-%m-%d")
                    except:
                        pass

                jobs.append({
                    "job_title":    title,
                    "company":      company.replace("-", " ").title(),
                    "location":     location,
                    "country":      extract_country(location),
                    "job_url":      job_url,
                    "jd_content":   content,
                    "source":       "lever",
                    "date_posted":  date_posted,
                })
                count += 1

            if count:
                print(f"  🔧 Lever | {company}: {count} jobs")

        except Exception:
            continue

        time.sleep(1)

    return jobs


# ==========================================================
# MAIN AGGREGATOR
# ==========================================================
def search_jobs():
    """Aggregate all sources, deduplicate by URL."""
    print("\n🔎 Aggressive scraping started...\n")

    all_jobs = []

    print("📡 Source 1: JobSpy (LinkedIn / Indeed / Glassdoor)")
    try:
        all_jobs.extend(search_jobspy())
    except Exception as e:
        print(f"  ❌ JobSpy failed: {e}")

    print("\n🌱 Source 2: Greenhouse startup boards")
    try:
        all_jobs.extend(search_greenhouse())
    except Exception as e:
        print(f"  ❌ Greenhouse failed: {e}")

    print("\n🔧 Source 3: Lever startup boards")
    try:
        all_jobs.extend(search_lever())
    except Exception as e:
        print(f"  ❌ Lever failed: {e}")

    # Deduplicate by URL
    seen = set()
    unique = []
    for job in all_jobs:
        url = job.get("job_url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(job)

    print(f"\n📊 Scraping complete: {len(all_jobs)} raw → {len(unique)} unique jobs")
    return unique


if __name__ == "__main__":
    print("🧪 Testing Aggressive Scraper...\n")
    jobs = search_jobs()
    print(f"\n✅ Total unique jobs: {len(jobs)}")
    if jobs:
        j = jobs[0]
        print(f"\nSample: {j['company']} — {j['job_title']} ({j['country']})")
