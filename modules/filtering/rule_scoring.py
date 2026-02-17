# modules/filtering/rule_scoring.py
"""
Weighted scoring system for job title + JD text.
Accept threshold: score >= 2
"""

import re
import logging

log = logging.getLogger(__name__)

# ── Title Signals ─────────────────────────────────────────────────────────────

TITLE_POSITIVE = [
    ("internship", 4),
    ("intern", 4),
    ("graduate", 3),
    ("new grad", 3),
    ("newgrad", 3),
    ("junior", 3),
    ("jr.", 3),
    ("fresher", 3),
    ("associate", 2),
    ("entry level", 2),
    ("entry-level", 2),
    ("trainee", 2),
    ("apprentice", 2),
    ("early career", 2),
    ("placement", 2),
    ("software engineer", 1),
    ("developer", 1),
    ("backend engineer", 1),
    ("frontend engineer", 1),
    ("full stack", 1),
    ("fullstack", 1),
    ("ai engineer", 1),
    ("ml engineer", 1),
    ("data engineer", 1),
    ("platform engineer", 1),
    ("devops engineer", 1),
    ("cloud engineer", 1),
    ("mobile engineer", 1),
    ("sre", 1),
    ("site reliability", 1),
]

TITLE_NEGATIVE = [
    ("senior", -6),
    ("sr.", -6),
    ("staff", -6),
    ("principal", -6),
    ("lead ", -6),
    ("tech lead", -6),
    ("architect", -6),
    ("manager", -6),
    ("director", -6),
    ("head of", -6),
    ("vp ", -6),
    ("vice president", -6),
    ("chief", -6),
    ("distinguished", -6),
    ("fellow", -5),
]

# ── JD Text Signals ──────────────────────────────────────────────────────────

JD_POSITIVE = [
    ("internship", 3),
    ("intern program", 3),
    ("summer intern", 3),
    ("0-2 years", 2),
    ("0–2 years", 2),
    ("0 to 2 years", 2),
    ("new grad", 2),
    ("new graduate", 2),
    ("recent graduate", 2),
    ("fresh graduate", 2),
    ("fresher", 2),
    ("entry level", 1),
    ("entry-level", 1),
    ("early career", 1),
    ("no experience required", 2),
    ("0-1 years", 2),
    ("1-2 years", 1),
    ("graduate program", 2),
    ("graduate scheme", 2),
    ("campus hiring", 2),
    ("university hiring", 2),
]

JD_NEGATIVE = [
    ("5+ years", -4),
    ("6+ years", -4),
    ("7+ years", -4),
    ("8+ years", -5),
    ("10+ years", -5),
    ("technical leadership", -3),
    ("extensive experience", -3),
    ("own architecture decisions", -3),
    ("deep expertise", -3),
    ("proven track record", -2),
    ("managed a team", -4),
    ("team leadership", -3),
    ("people management", -4),
    ("p&l responsibility", -5),
    ("strategic direction", -4),
    ("10 years of experience", -5),
    ("8 years of experience", -5),
    ("7 years of experience", -4),
    ("5 years of experience", -4),
    ("minimum 5 years", -4),
    ("at least 5 years", -4),
]

ACCEPT_THRESHOLD = 2


def score_job(title: str, description: str) -> tuple[int, list[str]]:
    """
    Score a job based on title + description signals.
    Returns (score, breakdown_list).
    Accept if score >= ACCEPT_THRESHOLD.
    """
    score = 0
    breakdown = []
    t = title.lower().strip()
    d = description.lower().strip() if description else ""

    # Title scoring
    for keyword, points in TITLE_POSITIVE:
        if keyword in t:
            score += points
            breakdown.append(f"title:+{points} '{keyword}'")

    for keyword, points in TITLE_NEGATIVE:
        if keyword in t:
            score += points
            breakdown.append(f"title:{points} '{keyword}'")

    # JD scoring
    for keyword, points in JD_POSITIVE:
        if keyword in d:
            score += points
            breakdown.append(f"jd:+{points} '{keyword}'")

    for keyword, points in JD_NEGATIVE:
        if keyword in d:
            score += points
            breakdown.append(f"jd:{points} '{keyword}'")

    return score, breakdown


def passes_rule_filter(title: str, description: str) -> tuple[bool, int, list[str]]:
    """
    Convenience wrapper. Returns (accepted, score, breakdown).
    """
    score, breakdown = score_job(title, description)
    accepted = score >= ACCEPT_THRESHOLD
    return accepted, score, breakdown
