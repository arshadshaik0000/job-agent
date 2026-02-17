# modules/tracker.py
"""
SQLite database layer.
Manages jobs, daily_stats, discovered_domains, and ai_validation_cache tables.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import hashlib
from datetime import datetime
from config import DB_PATH

import logging
log = logging.getLogger(__name__)


# ── Table Initialization ─────────────────────────────────────────────────────

def init_db():
    """Initialize all database tables."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Jobs table (with new relevance_score column)
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_title TEXT,
            company TEXT,
            country TEXT,
            job_url TEXT UNIQUE,
            visa_sponsorship TEXT,
            hr_score REAL,
            relevance_score INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            resume_version TEXT,
            skills_emphasized TEXT,
            date_found TEXT,
            date_applied TEXT,
            jd_content TEXT,
            notes TEXT,
            source TEXT DEFAULT ''
        )
    ''')

    # Add relevance_score column if it doesn't exist (migration)
    try:
        c.execute("ALTER TABLE jobs ADD COLUMN relevance_score INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Add source column if it doesn't exist (migration)
    try:
        c.execute("ALTER TABLE jobs ADD COLUMN source TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    # Daily stats table
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE,
            total_found INTEGER DEFAULT 0,
            total_applied INTEGER DEFAULT 0,
            india_applied INTEGER DEFAULT 0,
            international_applied INTEGER DEFAULT 0,
            sponsored_applied INTEGER DEFAULT 0,
            manual_review INTEGER DEFAULT 0,
            avg_hr_score REAL DEFAULT 0,
            resumes_created INTEGER DEFAULT 0
        )
    ''')

    # Discovered domains table
    c.execute('''
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
    ''')

    # AI validation cache table
    c.execute('''
        CREATE TABLE IF NOT EXISTS ai_validation_cache (
            job_hash TEXT PRIMARY KEY,
            decision TEXT NOT NULL,
            confidence INTEGER DEFAULT 0,
            reason TEXT DEFAULT '',
            validated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    log.info("✅ Database initialized (all tables ready)")


# ── Job Operations ────────────────────────────────────────────────────────────

def job_exists(job_url: str) -> bool:
    """Check if a job URL already exists in the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM jobs WHERE job_url = ?", (job_url,))
    result = c.fetchone()
    conn.close()
    return result is not None


def save_job(job_data: dict) -> int | None:
    """
    Save a job to the database.
    Returns job_id if saved, None if duplicate.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO jobs (
                job_title, company, country, job_url,
                visa_sponsorship, hr_score, relevance_score, status,
                resume_version, skills_emphasized,
                date_found, jd_content, notes, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job_data.get('job_title'),
            job_data.get('company'),
            job_data.get('country'),
            job_data.get('job_url'),
            job_data.get('visa_sponsorship', 'unknown'),
            job_data.get('hr_score', 0),
            job_data.get('relevance_score', 0),
            job_data.get('status', 'pending'),
            job_data.get('resume_version', ''),
            job_data.get('skills_emphasized', ''),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            job_data.get('jd_content', ''),
            job_data.get('notes', ''),
            job_data.get('source', ''),
        ))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def update_job_status(job_url: str, status: str,
                      resume_version: str = None, hr_score: float = None):
    """Update the status of a job."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if status == 'applied':
        c.execute('''
            UPDATE jobs SET status=?, date_applied=?, resume_version=?, hr_score=?
            WHERE job_url=?
        ''', (status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
              resume_version, hr_score, job_url))
    else:
        c.execute("UPDATE jobs SET status=? WHERE job_url=?", (status, job_url))
    conn.commit()
    conn.close()


# ── Stats Operations ──────────────────────────────────────────────────────────

def update_daily_stats(date: str, **kwargs):
    """Update daily stats counters."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM daily_stats WHERE date=?", (date,))
    if not c.fetchone():
        c.execute("INSERT INTO daily_stats (date) VALUES (?)", (date,))
    for key, value in kwargs.items():
        c.execute(f"UPDATE daily_stats SET {key}=? WHERE date=?", (value, date))
    conn.commit()
    conn.close()


def get_today_stats():
    """Get today's statistics."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute("SELECT * FROM daily_stats WHERE date=?", (today,))
    row = c.fetchone()
    conn.close()
    return row


def get_all_applied():
    """Get all applied jobs."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM jobs WHERE status='applied' ORDER BY date_applied DESC")
    rows = c.fetchall()
    conn.close()
    return rows


# ── Hash Utility ──────────────────────────────────────────────────────────────

def job_hash(job: dict) -> str:
    """Generate a unique hash for a job based on company, title, and country."""
    base = f"{job.get('company', '')}|{job.get('job_title', '')}|{job.get('country', '')}"
    return hashlib.md5(base.lower().encode()).hexdigest()