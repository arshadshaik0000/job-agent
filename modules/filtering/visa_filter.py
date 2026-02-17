# modules/filtering/visa_filter.py
"""
Visa/sponsorship scoring for international job postings.
India jobs auto-pass. Remote internships auto-pass.
"""

import logging

log = logging.getLogger(__name__)

SPONSORSHIP_POSITIVE = [
    ("visa sponsorship available", 3),
    ("visa sponsorship", 2),
    ("sponsorship available", 2),
    ("we sponsor", 2),
    ("will sponsor", 2),
    ("able to sponsor", 2),
    ("happy to sponsor", 2),
    ("open to sponsoring", 2),
    ("sponsoring visas", 2),
    ("sponsorship provided", 2),
    ("visa support provided", 2),
    ("visa provided", 2),
    ("visa support", 1),
    ("relocation support", 1),
    ("relocation assistance", 1),
    ("relocation package", 1),
    ("relocation budget", 1),
    ("relocation covered", 1),
    ("we cover relocation", 1),
    ("visa costs covered", 1),
    ("work permit provided", 2),
    ("work visa", 1),
    ("global mobility", 1),
    ("visa assistance", 1),
    ("international candidates welcome", 2),
    ("international applicants", 1),
    ("worldwide applicants", 1),
    ("global applicants", 1),
]

SPONSORSHIP_NEGATIVE = [
    ("no sponsorship", -5),
    ("cannot sponsor", -5),
    ("unable to sponsor", -5),
    ("not able to sponsor", -5),
    ("do not sponsor", -5),
    ("don't sponsor", -5),
    ("must have work authorization", -3),
    ("must be authorized", -3),
    ("must be eligible to work", -3),
    ("must have right to work", -3),
    ("proof of eligibility", -2),
    ("no visa support", -4),
    ("citizens only", -5),
    ("permanent residents only", -5),
    ("us citizens only", -5),
    ("no relocation", -2),
]

INDIA_KEYWORDS = ["india", "bangalore", "bengaluru", "hyderabad", "pune",
                   "chennai", "mumbai", "delhi", "noida", "gurgaon",
                   "gurugram", "kolkata", "ahmedabad", "jaipur", "kochi"]

INTERNSHIP_KEYWORDS = ["intern", "internship", "trainee", "apprentice"]


def check_visa(title: str, description: str, country: str,
               is_remote: bool = False) -> tuple[bool, int, str]:
    """
    Returns (passed, score, reason).
    India jobs auto-pass.
    Remote internships auto-pass.
    International jobs need positive sponsorship score.
    """
    c = country.lower().strip()
    t = title.lower()
    d = description.lower() if description else ""

    # India auto-pass
    if any(k in c for k in INDIA_KEYWORDS):
        return True, 99, "India — no sponsorship needed"

    # Remote internship auto-pass
    is_intern = any(k in t for k in INTERNSHIP_KEYWORDS)
    if is_remote and is_intern:
        return True, 50, "Remote internship — auto-pass"

    # Score sponsorship signals
    score = 0
    reasons = []

    for keyword, points in SPONSORSHIP_POSITIVE:
        if keyword in d:
            score += points
            reasons.append(f"+{points} '{keyword}'")

    for keyword, points in SPONSORSHIP_NEGATIVE:
        if keyword in d:
            score += points
            reasons.append(f"{points} '{keyword}'")

    if score >= 1:
        return True, score, f"Sponsorship likely: {'; '.join(reasons[:3])}"

    if score < -2:
        return False, score, f"No sponsorship: {'; '.join(reasons[:3])}"

    # Neutral — no strong signal either way
    return False, score, "No sponsorship info for international role"
