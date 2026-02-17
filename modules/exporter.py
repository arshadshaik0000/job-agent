# modules/exporter.py
import sqlite3
from openpyxl import Workbook
from config import DB_PATH
from datetime import datetime


def export_jobs_to_excel(filepath="jobs_export.xlsx"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        SELECT
            job_title,
            company,
            country,
            visa_sponsorship,
            hr_score,
            status,
            resume_version,
            skills_emphasized,
            date_found,
            date_applied,
            job_url
        FROM jobs
        WHERE DATE(date_found) = DATE('now','localtime')
        ORDER BY date_found DESC

    """)

    rows = c.fetchall()
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Jobs"

    # Header row
    headers = [
        "Job Title", "Company", "Country", "Visa",
        "HR Score", "Status", "Resume Version",
        "Skills", "Date Found", "Date Applied", "URL"
    ]
    ws.append(headers)

    # Add data
    for row in rows:
        ws.append(list(row))

    # Auto width
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        ws.column_dimensions[column].width = min(max_length + 2, 50)

    wb.save(filepath)

    print(f"📊 Excel exported → {filepath}")
