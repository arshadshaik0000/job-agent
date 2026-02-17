# modules/filtering/ollama_validator.py
"""
Final AI validation layer using local Ollama.
Calls POST http://localhost:11434/api/generate
Caches results in SQLite to avoid re-validation.
"""

import json
import hashlib
import sqlite3
import re
import logging
import requests
from bs4 import BeautifulSoup

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import DB_PATH

log = logging.getLogger(__name__)

# ── Defaults (overridden by config if available) ──────────────────────────────

try:
    from config import OLLAMA_MODEL, OLLAMA_URL
except ImportError:
    OLLAMA_MODEL = "llama3:latest"
    OLLAMA_URL = "http://localhost:11434/api/generate"

MAX_JD_CHARS = 2000
TIMEOUT = 10
MAX_RETRIES = 1

PROMPT_TEMPLATE = """You are a strict hiring classifier.

The candidate is a **2025 graduate (B.Tech CSE — AI & ML specialization)**.

Classify whether this job is suitable for:
- Internship
- Fresher
- Entry-level (0–2 years)

Return ONLY valid JSON — no explanation, no markdown, no extra text:

{{"decision": "ACCEPT" or "REJECT", "confidence": 0-100, "reason": "short explanation"}}

RULES:
- ACCEPT internships aligned with software engineering, backend, AI/ML, full-stack, data engineering
- ACCEPT graduate/junior/entry-level roles (0-2 years experience)
- REJECT senior/lead/staff/principal/architect/manager/director roles
- REJECT roles requiring 3+ years of experience
- REJECT managerial, architecture-heavy, or executive roles
- If unclear, lean towards ACCEPT for entry-level-sounding roles

Job Title:
{title}

Job Description (first 2000 chars):
{description}"""


# ── SQLite Cache ──────────────────────────────────────────────────────────────

def init_ai_cache():
    """Create the AI validation cache table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS ai_validation_cache (
            job_hash TEXT PRIMARY KEY,
            decision TEXT NOT NULL,
            confidence INTEGER DEFAULT 0,
            reason TEXT DEFAULT '',
            validated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def get_cached_result(job_hash: str) -> dict | None:
    """Check cache for a previous validation result."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT decision, confidence, reason FROM ai_validation_cache WHERE job_hash = ?",
        (job_hash,)
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {"decision": row[0], "confidence": row[1], "reason": row[2]}
    return None


def cache_result(job_hash: str, result: dict):
    """Save validation result to cache."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            "INSERT OR REPLACE INTO ai_validation_cache (job_hash, decision, confidence, reason) VALUES (?, ?, ?, ?)",
            (job_hash, result.get("decision", "REJECT"),
             result.get("confidence", 0), result.get("reason", ""))
        )
        conn.commit()
    except Exception as e:
        log.warning(f"Cache write failed: {e}")
    finally:
        conn.close()


# ── Helpers ───────────────────────────────────────────────────────────────────

def compute_job_hash(title: str, description: str) -> str:
    """Generate hash from title + first 500 chars of description."""
    raw = f"{title.lower().strip()}|{description[:500].lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    if not text:
        return ""
    if "<" in text and ">" in text:
        return BeautifulSoup(text, "html.parser").get_text(separator=" ", strip=True)
    return text


def parse_ollama_response(text: str) -> dict | None:
    """Extract JSON from Ollama response, handling markdown code blocks."""
    text = text.strip()

    # Try direct JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code blocks
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding JSON-like content with braces
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


# ── Main Validator ────────────────────────────────────────────────────────────

def call_ollama(prompt: str, retries: int = MAX_RETRIES) -> dict | None:
    """Call the local Ollama API and parse the response."""
    for attempt in range(retries + 1):
        try:
            resp = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 200,
                    }
                },
                timeout=TIMEOUT,
            )
            if resp.status_code != 200:
                log.warning(f"Ollama HTTP {resp.status_code} (attempt {attempt + 1})")
                continue

            raw = resp.json().get("response", "")
            parsed = parse_ollama_response(raw)

            if parsed and "decision" in parsed:
                # Normalize decision
                decision = parsed.get("decision", "").upper().strip()
                if decision not in ("ACCEPT", "REJECT"):
                    decision = "REJECT"
                parsed["decision"] = decision
                parsed["confidence"] = int(parsed.get("confidence", 0))
                return parsed
            else:
                log.warning(f"Ollama invalid JSON (attempt {attempt + 1}): {raw[:100]}")

        except requests.exceptions.ConnectionError:
            log.warning("Ollama is offline — skipping AI validation")
            return None
        except requests.exceptions.Timeout:
            log.warning(f"Ollama timeout (attempt {attempt + 1})")
        except Exception as e:
            log.warning(f"Ollama error (attempt {attempt + 1}): {e}")

    return None


def validate_with_ollama(title: str, description: str, job_hash: str = None) -> dict:
    """
    Validate a job posting with the local Ollama model.

    Returns:
        dict with keys: decision, confidence, reason, source
        source is 'cache', 'ollama', or 'fallback'
    """
    # Compute hash if not provided
    if not job_hash:
        job_hash = compute_job_hash(title, description)

    # Check cache first
    cached = get_cached_result(job_hash)
    if cached:
        cached["source"] = "cache"
        return cached

    # Clean description
    clean_desc = strip_html(description)
    clean_desc = clean_desc[:MAX_JD_CHARS]

    # Build prompt
    prompt = PROMPT_TEMPLATE.format(
        title=title.strip(),
        description=clean_desc if clean_desc else "No description available."
    )

    # Call Ollama
    result = call_ollama(prompt)

    if result:
        result["source"] = "ollama"
        cache_result(job_hash, result)
        return result

    # Fallback — Ollama is offline or failed
    log.info("⚠️  Ollama unavailable — using fallback (ACCEPT with low confidence)")
    fallback = {
        "decision": "ACCEPT",
        "confidence": 30,
        "reason": "Ollama offline — fallback accept",
        "source": "fallback"
    }
    return fallback


# ── Initialize on import ─────────────────────────────────────────────────────

init_ai_cache()
