"""
main.py — Aggressive Job Discovery Agent
Scans every 60 minutes. Filters, saves to SQLite, sends Telegram alerts.
NO HR review. NO resume. NO applying. JUST discovery.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

from modules.scraper import search_jobs
from modules.tracker import init_db, job_exists, save_job
from modules.notifier import send_message, notify_job_found

from config import (
    SPONSORSHIP_KEYWORDS,
    NON_ENGLISH_KEYWORDS,
    REJECT_TITLE_KEYWORDS,
)


# ==========================================================
# FILTER FUNCTIONS
# ==========================================================

def contains_sponsorship(text):
    """Check if text mentions visa sponsorship."""
    text = (text or "").lower()
    return any(k in text for k in SPONSORSHIP_KEYWORDS)


def requires_non_english(text):
    """Check if job requires a non-English language."""
    text = (text or "").lower()
    return any(k in text for k in NON_ENGLISH_KEYWORDS)


def is_entry_level(title):
    """Reject senior/lead/director roles."""
    title_lower = (title or "").lower()
    return not any(k in title_lower for k in REJECT_TITLE_KEYWORDS)


def is_valid_job(job):
    """
    🇮🇳 India → allow all entry-level English jobs
    🌍 International → ONLY if sponsorship mentioned
    ❌ Non-English required → skip
    ❌ Senior/Lead/Director → skip
    """
    title       = job.get("job_title", "") or ""
    description = job.get("jd_content", "") or ""
    country     = job.get("country", "") or ""
    full_text   = title + " " + description

    # ❌ Non-English required
    if requires_non_english(full_text):
        return False

    # ❌ Senior / Lead / Director
    if not is_entry_level(title):
        return False

    # 🇮🇳 India — allow all valid entry-level
    if "india" in country.lower():
        return True

    # 🌍 International — MUST mention sponsorship
    if contains_sponsorship(description):
        return True

    # ❓ Sponsorship unclear → SKIP
    return False


# ==========================================================
# MAIN SCAN FUNCTION
# ==========================================================

def scan_jobs():
    """Discover → Filter → Save → Notify"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'='*55}")
    print(f"🔎 Scan started at {timestamp}")
    print(f"{'='*55}\n")

    jobs = search_jobs()

    print(f"\n📊 Total unique jobs from scraper: {len(jobs)}")

    new_count         = 0
    skipped_filter    = 0
    skipped_duplicate = 0

    for job in jobs:

        if not is_valid_job(job):
            skipped_filter += 1
            continue

        job_url = job.get("job_url", "")
        if not job_url or job_exists(job_url):
            skipped_duplicate += 1
            continue

        # Enrich
        job["visa_sponsorship"] = (
            "sponsored" if contains_sponsorship(job.get("jd_content", ""))
            else "not_required"
        )
        job["status"]   = "discovered"
        job["hr_score"] = 0
        job["notes"]    = f"Source: {job.get('source', 'unknown')}"

        # Save
        save_job(job)

        # Notify
        try:
            notify_job_found(job)
        except Exception as e:
            print(f"  ⚠️ Telegram failed: {e}")

        new_count += 1
        time.sleep(2)

    # Summary
    print(f"\n📊 Scan Summary:")
    print(f"  ✅ New jobs sent:   {new_count}")
    print(f"  🔍 Filtered out:   {skipped_filter}")
    print(f"  🔁 Duplicates:     {skipped_duplicate}")

    if new_count > 0:
        try:
            send_message(
                f"📊 *Scan Complete — {timestamp}*\n"
                f"✅ New jobs: {new_count}\n"
                f"🔍 Filtered: {skipped_filter}\n"
                f"🔁 Duplicates: {skipped_duplicate}"
            )
        except:
            pass


# ==========================================================
# ENTRY POINT
# ==========================================================

if __name__ == "__main__":

    print("\n🚀 Aggressive Job Discovery Agent Started")
    print("📡 Sources: LinkedIn, Indeed, Glassdoor, Greenhouse, Lever")
    print("⏱  Interval: every 60 minutes")
    print("🌍 Regions: India, UK, Germany, Netherlands, Ireland, UAE, Sweden, Poland, Spain, Remote\n")

    init_db()

    # Run immediately
    scan_jobs()

    # Schedule recurring
    scheduler = BlockingScheduler()
    scheduler.add_job(scan_jobs, "interval", minutes=60)

    print("\n⏰ Next scan in 60 minutes. Press Ctrl+C to stop.\n")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n👋 Agent stopped")
