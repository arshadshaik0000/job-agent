# modules/filtering/experience_parser.py
"""
Extract years-of-experience from JD text.
Reject if minimum required >= 3 years.
Internship roles auto-pass.
"""

import re
import logging

log = logging.getLogger(__name__)

# Patterns that indicate required experience
EXPERIENCE_PATTERNS = [
    # "5+ years", "5+ yrs"
    re.compile(r"(\d+)\s*\+\s*(?:years|yrs)", re.IGNORECASE),
    # "5-7 years", "5–7 years"
    re.compile(r"(\d+)\s*[-–]\s*\d+\s*(?:years|yrs)", re.IGNORECASE),
    # "minimum 5 years", "at least 5 years"
    re.compile(r"(?:minimum|at least|min\.?)\s*(?:of\s+)?(\d+)\s*(?:years|yrs)", re.IGNORECASE),
    # "5 years of experience"
    re.compile(r"(\d+)\s*(?:years|yrs)\s*(?:of\s+)?(?:experience|exp)", re.IGNORECASE),
    # "X years' experience" (possessive)
    re.compile(r"(\d+)\s*(?:years|yrs)['']\s*(?:experience|exp)", re.IGNORECASE),
    # "experience: 5 years"
    re.compile(r"experience\s*[:=]\s*(\d+)\s*(?:years|yrs)", re.IGNORECASE),
]

INTERNSHIP_TITLE_KEYWORDS = [
    "intern",
    "internship",
    "trainee",
    "apprentice",
    "placement",
    "co-op",
    "coop",
]


def extract_experience(text: str) -> int:
    """
    Extract the maximum years-of-experience mentioned in text.
    Returns 0 if no patterns found.
    """
    if not text:
        return 0

    text = text.lower()
    all_years = []

    for pattern in EXPERIENCE_PATTERNS:
        matches = pattern.findall(text)
        for m in matches:
            try:
                val = int(m)
                if 0 <= val <= 30:  # sanity bound
                    all_years.append(val)
            except (ValueError, TypeError):
                continue

    return max(all_years) if all_years else 0


def is_internship_title(title: str) -> bool:
    """Check if the title indicates an internship role."""
    t = title.lower()
    return any(k in t for k in INTERNSHIP_TITLE_KEYWORDS)


def passes_experience_filter(title: str, description: str) -> tuple[bool, int, str]:
    """
    Returns (passed, years_found, reason).
    Internships auto-pass.
    Reject if minimum experience >= 3.
    """
    # Internship roles auto-pass
    if is_internship_title(title):
        return True, 0, "Internship role — auto-pass"

    years = extract_experience(description)

    if years >= 3:
        return False, years, f"Requires {years}+ years experience"

    if years == 0:
        return True, 0, "No experience requirement found"

    return True, years, f"Requires {years} years — acceptable"
