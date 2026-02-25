# modules/tracker.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from datetime import datetime
from config import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_title TEXT,
            company TEXT,
            country TEXT,
            job_url TEXT UNIQUE,
            visa_sponsorship TEXT,
            hr_score REAL,
            status TEXT DEFAULT 'discovered',
            resume_version TEXT,
            skills_emphasized TEXT,
            date_found TEXT,
            date_applied TEXT,
            jd_content TEXT,
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ Database initialized!")

def job_exists(job_url):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM jobs WHERE job_url = ?", (job_url,))
    result = c.fetchone()
    conn.close()
    return result is not None

def save_job(job_data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO jobs (
                job_title, company, country, job_url,
                visa_sponsorship, hr_score, status,
                resume_version, skills_emphasized,
                date_found, jd_content, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job_data.get('job_title'),
            job_data.get('company'),
            job_data.get('country'),
            job_data.get('job_url'),
            job_data.get('visa_sponsorship', 'unknown'),
            job_data.get('hr_score', 0),
            job_data.get('status', 'discovered'),
            job_data.get('resume_version', ''),
            job_data.get('skills_emphasized', ''),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            job_data.get('jd_content', ''),
            job_data.get('notes', '')
        ))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()