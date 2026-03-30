"""
RemoteOK JSON API — free, no auth required.
Docs: https://remoteok.com/api
"""
from .base import build_job, get, is_relevant, sleep_between

SOURCE = "RemoteOK"
API_URL = "https://remoteok.com/api"

CREATIVE_TAGS = {
    "design",
    "creative",
    "art",
    "ux",
    "ui",
    "brand",
    "marketing",
    "creative director",
    "art director",
}

TARGET_TITLES = [
    "creative director",
    "creative technologist",
    "head of creative",
    "senior art director",
    "executive creative director",
    "chief creative",
    "vp creative",
]


def fetch() -> list[dict]:
    resp = get(API_URL, headers={"Accept": "application/json"})
    if not resp:
        return []

    try:
        data = resp.json()
    except Exception:
        return []

    jobs = []
    for item in data:
        if not isinstance(item, dict):
            continue

        title = item.get("position", "")
        company = item.get("company", "")
        url = item.get("url", "") or f"https://remoteok.com/remote-jobs/{item.get('id', '')}"
        description = item.get("description", "")
        tags = [t.lower() for t in (item.get("tags") or [])]
        salary = ""
        salary_min = item.get("salary_min")
        salary_max = item.get("salary_max")
        if salary_min or salary_max:
            salary = f"${salary_min or '?'}–${salary_max or '?'}"

        date_posted = item.get("date", "")

        title_lower = title.lower()
        tag_match = bool(CREATIVE_TAGS & set(tags))
        title_match = any(t in title_lower for t in TARGET_TITLES)

        if not (title_match or (tag_match and is_relevant(title, description))):
            continue

        jobs.append(
            build_job(
                title=title,
                company=company,
                location="Remote",
                url=url,
                source=SOURCE,
                description=description,
                salary=salary,
                date_posted=date_posted,
            )
        )

    sleep_between()
    return jobs
