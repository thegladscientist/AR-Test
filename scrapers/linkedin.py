"""
LinkedIn Jobs — public HTML scraper (no auth).
Searches remote creative director / technologist roles.
"""
from bs4 import BeautifulSoup

from .base import build_job, get, is_relevant, is_location_ok, sleep_between

SOURCE = "LinkedIn"
BASE_URL = "https://www.linkedin.com/jobs/search"

SEARCH_CONFIGS = [
    {"keywords": "creative director", "f_WT": "2", "location": "Worldwide"},
    {"keywords": "creative technologist", "f_WT": "2", "location": "Worldwide"},
    {"keywords": "senior art director", "f_WT": "2", "location": "Worldwide"},
    {"keywords": "creative director", "location": "Barcelona, Catalonia, Spain"},
]


def _parse_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    for card in soup.find_all("div", class_=lambda c: c and "job-search-card" in (c or "")):
        title_el = card.find("h3", class_=lambda c: c and "base-search-card__title" in (c or ""))
        title = title_el.get_text(strip=True) if title_el else ""
        if not title or not is_relevant(title):
            continue

        company_el = card.find("h4", class_=lambda c: c and "base-search-card__subtitle" in (c or ""))
        company = company_el.get_text(strip=True) if company_el else ""

        loc_el = card.find("span", class_=lambda c: c and "job-search-card__location" in (c or ""))
        location = loc_el.get_text(strip=True) if loc_el else ""
        if not is_location_ok(location):
            continue

        link_el = card.find("a", class_=lambda c: c and "base-card__full-link" in (c or ""))
        url = link_el["href"].split("?")[0] if link_el else ""

        date_el = card.find("time")
        date_posted = date_el.get("datetime", "") if date_el else ""

        jobs.append(
            build_job(
                title=title,
                company=company,
                location=location,
                url=url,
                source=SOURCE,
                date_posted=date_posted,
            )
        )
    return jobs


def fetch() -> list[dict]:
    seen = set()
    results = []

    for config in SEARCH_CONFIGS:
        resp = get(BASE_URL, params=config)
        if resp:
            for job in _parse_page(resp.text):
                if job["hash"] not in seen:
                    seen.add(job["hash"])
                    results.append(job)
        sleep_between(2, 4)

    return results
