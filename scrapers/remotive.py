"""
Remotive JSON API — free, no auth required.
Docs: https://remotive.com/api/remote-jobs
"""
from .base import build_job, get, is_relevant, sleep_between

SOURCE = "Remotive"
BASE_URL = "https://remotive.com/api/remote-jobs"

SEARCH_QUERIES = [
    "creative director",
    "creative technologist",
    "art director",
]


def _fetch_query(query: str) -> list[dict]:
    resp = get(BASE_URL, params={"search": query, "limit": 20})
    if not resp:
        return []
    try:
        data = resp.json()
    except Exception:
        return []

    jobs = []
    for item in data.get("jobs", []):
        title = item.get("title", "")
        if not is_relevant(title):
            continue

        company = item.get("company_name", "")
        url = item.get("url", "")
        description = item.get("description", "")
        # Strip HTML tags from description
        try:
            from bs4 import BeautifulSoup
            description = BeautifulSoup(description, "lxml").get_text(" ", strip=True)
        except Exception:
            pass
        salary = item.get("salary", "") or ""
        date_posted = item.get("publication_date", "")
        candidate_location = item.get("candidate_required_location", "Remote")

        jobs.append(
            build_job(
                title=title,
                company=company,
                location=candidate_location or "Remote",
                url=url,
                source=SOURCE,
                description=description,
                salary=salary,
                date_posted=date_posted,
            )
        )
    return jobs


def fetch() -> list[dict]:
    seen_hashes = set()
    results = []
    for query in SEARCH_QUERIES:
        for job in _fetch_query(query):
            if job["hash"] not in seen_hashes:
                seen_hashes.add(job["hash"])
                results.append(job)
        sleep_between(1, 2)
    return results
