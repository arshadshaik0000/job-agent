# main.py
"""
Autonomous Global Web Job Discovery Agent
10-step pipeline: Discover → Crawl → Parse → Rule Score → Experience →
                  Visa → Ollama → Save → Notify → Export
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import hashlib
import logging
from datetime import datetime

from modules.tracker import init_db, job_exists, save_job, job_hash

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s — %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__)


# ── Deduplication ─────────────────────────────────────────────────────────────

def deduplicate(jobs: list[dict]) -> list[dict]:
    """Remove duplicate jobs by URL and hash."""
    seen_urls = set()
    seen_hashes = set()
    unique = []

    for job in jobs:
        url = job.get('job_url', '')
        h = job_hash(job)

        if (url and url in seen_urls) or h in seen_hashes:
            continue

        seen_urls.add(url)
        seen_hashes.add(h)
        unique.append(job)

    return unique


# ── Step 1-3: Collect Jobs from All Sources ───────────────────────────────────

def collect_all_jobs() -> list[dict]:
    """Collect jobs from ATS platforms, JobSpy, and web discovery."""
    all_jobs = []

    # ── ATS Platform Scrapers ──
    log.info("━" * 55)
    log.info("📡 STEP 1-3: Collecting jobs from all sources...")
    log.info("━" * 55)

    # Greenhouse
    try:
        from modules.parsing.greenhouse import scrape_greenhouse
        all_jobs += scrape_greenhouse()
    except Exception as e:
        log.warning(f"Greenhouse failed: {e}")

    # Lever
    try:
        from modules.parsing.lever import scrape_lever
        all_jobs += scrape_lever()
    except Exception as e:
        log.warning(f"Lever failed: {e}")

    # Ashby
    try:
        from modules.parsing.ashby import scrape_ashby
        all_jobs += scrape_ashby()
    except Exception as e:
        log.warning(f"Ashby failed: {e}")

    # Workable
    try:
        from modules.parsing.workable import scrape_workable
        all_jobs += scrape_workable()
    except Exception as e:
        log.warning(f"Workable failed: {e}")

    # JobSpy (LinkedIn + Indeed)
    try:
        from jobspy import scrape_jobs
        from config import JOBSPY_SEARCHES

        log.info(f"🌍 Scraping JobSpy ({len(JOBSPY_SEARCHES)} searches)...")
        for search in JOBSPY_SEARCHES:
            try:
                df = scrape_jobs(
                    site_name=["linkedin", "indeed"],
                    search_term=search["term"],
                    location=search["location"],
                    results_wanted=15,
                    hours_old=48,
                    linkedin_fetch_description=False,
                    country_indeed="India" if search["country"] == "India" else "worldwide",
                )
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        url = str(row.get("job_url", ""))
                        if not url or url == "nan":
                            continue
                        all_jobs.append({
                            "job_title": str(row.get("title", "")),
                            "company": str(row.get("company", "")),
                            "country": search["country"],
                            "job_url": url,
                            "jd_content": str(row.get("description", "")),
                            "source": "jobspy",
                            "visa_sponsorship": "unknown",
                            "date_found": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "status": "found",
                            "hr_score": 0,
                        })
                time.sleep(2)
            except Exception as e:
                log.warning(f"  JobSpy [{search['term'][:25]}]: {e}")

        log.info(f"  ✅ JobSpy complete")
    except Exception as e:
        log.warning(f"JobSpy module failed: {e}")

    # ── Web Discovery + Crawl ──
    try:
        from modules.discovery.web_discovery import discover_domains, get_uncrawled_domains, mark_crawled
        from modules.crawling.career_crawler import run_crawler
        from modules.parsing.generic_html import parse_job_page

        # Discover new domains
        new_domains = discover_domains(batch_size=10)
        log.info(f"  🌍 New domains discovered: {len(new_domains)}")

        # Get domains to crawl (new + stale)
        domains_to_crawl = get_uncrawled_domains(limit=20)

        if domains_to_crawl:
            # Crawl career pages
            domain_jobs = run_crawler(domains_to_crawl)

            # Parse individual job pages
            for domain, job_urls in domain_jobs.items():
                parsed_count = 0
                for url in job_urls[:10]:  # Limit per domain
                    try:
                        parsed = parse_job_page(url)
                        if parsed:
                            parsed["date_found"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            parsed["status"] = "found"
                            parsed["hr_score"] = 0
                            all_jobs.append(parsed)
                            parsed_count += 1
                    except Exception as e:
                        log.debug(f"Parse error {url[:50]}: {e}")

                mark_crawled(domain, parsed_count)

    except Exception as e:
        log.warning(f"Web discovery/crawl failed: {e}")

    return all_jobs


# ── Steps 4-7: Filter Pipeline ───────────────────────────────────────────────

def filter_jobs(jobs: list[dict]) -> list[dict]:
    """Apply the full filter pipeline: Rule Score → Experience → Visa → Ollama."""
    from modules.filtering.rule_scoring import passes_rule_filter
    from modules.filtering.experience_parser import passes_experience_filter
    from modules.filtering.visa_filter import check_visa
    from modules.filtering.ollama_validator import validate_with_ollama, compute_job_hash
    from modules.parsing.generic_html import fetch_full_jd

    log.info("━" * 55)
    log.info("🔬 STEPS 4-7: Filtering pipeline...")
    log.info("━" * 55)

    passed = []
    total = len(jobs)
    stats = {"rule": 0, "exp": 0, "visa": 0, "ollama": 0, "passed": 0}

    for i, job in enumerate(jobs, 1):
        title = job.get("job_title", "")
        desc = job.get("jd_content", "")
        country = job.get("country", "")
        url = job.get("job_url", "")

        if i % 50 == 0:
            log.info(f"  📊 Progress: {i}/{total} | Passed so far: {stats['passed']}")

        # Fetch full JD if too short
        if len(desc) < 300 and url:
            try:
                full_jd = fetch_full_jd(url)
                if full_jd:
                    desc = full_jd
                    job["jd_content"] = desc
            except Exception:
                pass

        # STEP 4: Rule scoring filter
        rule_ok, score, breakdown = passes_rule_filter(title, desc)
        if not rule_ok:
            stats["rule"] += 1
            continue

        # STEP 5: Experience filter
        exp_ok, years, exp_reason = passes_experience_filter(title, desc)
        if not exp_ok:
            stats["exp"] += 1
            continue

        # STEP 6: Visa filter
        is_remote = "remote" in country.lower() or "remote" in title.lower()
        visa_ok, visa_score, visa_reason = check_visa(title, desc, country, is_remote)
        if not visa_ok:
            stats["visa"] += 1
            continue

        # STEP 7: Ollama AI validation (FINAL AUTHORITY)
        jh = compute_job_hash(title, desc)
        ai_result = validate_with_ollama(title, desc, jh)

        if ai_result.get("decision") == "REJECT":
            stats["ollama"] += 1
            log.debug(f"  🤖 Ollama REJECT: {title[:40]} — {ai_result.get('reason', '')}")
            continue

        # PASSED ALL FILTERS
        job["relevance_score"] = score
        job["visa_sponsorship"] = "sponsored" if visa_score > 1 else "not_required" if "india" in country.lower() else "unknown"
        job["notes"] = f"Score:{score} | AI:{ai_result.get('confidence', 0)}% | {ai_result.get('reason', '')}"

        passed.append(job)
        stats["passed"] += 1

        log.info(f"  ✅ [{i}/{total}] {job.get('company', '')[:20]} — {title[:35]} [{country[:15]}]")

    log.info(f"\n📊 Filter Results:")
    log.info(f"   Rule rejected: {stats['rule']}")
    log.info(f"   Experience rejected: {stats['exp']}")
    log.info(f"   Visa rejected: {stats['visa']}")
    log.info(f"   Ollama rejected: {stats['ollama']}")
    log.info(f"   ✅ Passed: {stats['passed']}/{total}")

    return passed


# ── Steps 8-10: Save, Notify, Export ──────────────────────────────────────────

def process_results(jobs: list[dict]):
    """Save new jobs, send Telegram notifications, and export to Excel."""
    from modules.notifier import notify_job_found

    log.info("━" * 55)
    log.info("💾 STEPS 8-10: Save → Notify → Export")
    log.info("━" * 55)

    new_count = 0
    skip_count = 0

    for job in jobs:
        url = job.get("job_url", "")

        # Skip if already exists
        if job_exists(url):
            skip_count += 1
            continue

        # STEP 8: Save
        job["status"] = "found"
        saved_id = save_job(job)

        if not saved_id:
            skip_count += 1
            continue

        new_count += 1

        # STEP 9: Notify via Telegram
        try:
            notify_job_found(job)
        except Exception as e:
            log.warning(f"  Telegram error: {e}")

        log.info(f"  💾 Saved: {job.get('company', '')} — {job.get('job_title', '')} [{job.get('source', '')}]")
        time.sleep(1)

    # STEP 10: Export
    try:
        from modules.exporter import export_jobs_to_excel
        export_jobs_to_excel()
    except Exception as e:
        log.warning(f"  Export failed: {e}")

    log.info(f"\n✅ New jobs saved: {new_count} | Skipped (duplicates): {skip_count}")


# ── Main Scan Cycle ───────────────────────────────────────────────────────────

def scan_jobs():
    """Run one complete scan cycle through the 10-step pipeline."""
    log.info("=" * 55)
    log.info(f"🔎 SCAN CYCLE [{datetime.now().strftime('%Y-%m-%d %H:%M')}]")
    log.info("=" * 55)

    # Steps 1-3: Collect
    all_jobs = collect_all_jobs()
    log.info(f"\n📊 Total raw jobs collected: {len(all_jobs)}")

    # Deduplicate
    unique = deduplicate(all_jobs)
    log.info(f"📊 After deduplication: {len(unique)}")

    # Remove already-saved jobs early
    unseen = [j for j in unique if not job_exists(j.get("job_url", ""))]
    log.info(f"📊 Unseen (new) jobs: {len(unseen)}")

    if not unseen:
        log.info("ℹ️  No new jobs to process this cycle")
        return

    # Steps 4-7: Filter
    passed = filter_jobs(unseen)

    if not passed:
        log.info("ℹ️  No jobs passed all filters this cycle")
        return

    # Steps 8-10: Save, Notify, Export
    process_results(passed)

    log.info("=" * 55)


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from config import SCAN_INTERVAL_SECONDS

    print("\n" + "=" * 55)
    print("🚀 Autonomous Job Discovery Agent — Started")
    print(f"   Scan interval: {SCAN_INTERVAL_SECONDS}s")
    print(f"   Pipeline: Discover → Crawl → Parse → Score → Exp → Visa → AI → Save → Notify → Export")
    print("=" * 55 + "\n")

    init_db()

    while True:
        try:
            log.info("🔁 Starting new scan cycle...\n")
            scan_jobs()

            log.info(f"⏳ Waiting {SCAN_INTERVAL_SECONDS}s before next scan...\n")
            time.sleep(SCAN_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\n👋 Agent stopped")
            break
        except Exception as e:
            log.error(f"❌ Scan cycle error: {e}", exc_info=True)
            time.sleep(30)
