import hashlib
import random
import time
from datetime import datetime, timezone

import requests

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
]

SEARCH_TERMS = [
    "creative director",
    "creative technologist",
    "head of creative",
    "senior art director",
]

BARCELONA_TERMS = ["Barcelona", "barcelona"]


def make_hash(title: str, company: str, url: str) -> str:
    raw = f"{title.lower().strip()}|{company.lower().strip()}|{url.strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def random_ua() -> str:
    return random.choice(USER_AGENTS)


def get(url: str, **kwargs) -> requests.Response | None:
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", random_ua())
    try:
        resp = requests.get(url, headers=headers, timeout=12, **kwargs)
        resp.raise_for_status()
        return resp
    except Exception:
        return None


def sleep_between(min_s: float = 1.0, max_s: float = 3.0):
    time.sleep(random.uniform(min_s, max_s))


def is_relevant(title: str, description: str = "") -> bool:
    """Return True if the job title/description matches our target roles."""
    text = (title + " " + description).lower()
    keywords = [
        "creative director",
        "creative technologist",
        "head of creative",
        "chief creative",
        "vp creative",
        "vp of creative",
        "director of creative",
        "senior art director",
        "executive creative",
        "design director",
        "creative lead",
        "art director",
        "experience director",
        "group creative director",
        "associate creative director",
        "head of design",
        "creative",
        "design"
    ]
    return any(k in text for k in keywords)


def is_location_ok(location: str) -> bool:
    """Return True if the location is remote or Barcelona."""
    loc = location.lower()
    return (
        "remote" in loc
        or "anywhere" in loc
        or "worldwide" in loc
        or "barcelona" in loc
        or "spain" in loc
        or "united states" in loc
        or "usa" in loc
        or "united kingdom" in loc
        or "uk" in loc
        or "europe" in loc
        or location == ""
    )


def build_job(
    title: str,
    company: str,
    location: str,
    url: str,
    source: str,
    description: str = "",
    salary: str = "",
    date_posted: str = "",
) -> dict:
    return {
        "hash": make_hash(title, company, url),
        "title": title.strip(),
        "company": company.strip(),
        "location": location.strip(),
        "salary": salary.strip() if salary else None,
        "description": description.strip()[:600] if description else None,
        "url": url.strip(),
        "source": source,
        "date_posted": date_posted or None,
        "date_fetched": now_iso(),
    }
