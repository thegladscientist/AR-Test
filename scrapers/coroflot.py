"""
Coroflot — HTML scraper.
https://www.coroflot.com/design-jobs
"""
from bs4 import BeautifulSoup

from .base import build_job, get, is_relevant, is_location_ok, sleep_between

SOURCE = "Coroflot"
SEARCH_TERMS = ["creative director", "creative technologist", "art director"]
BASE_URL = "https://www.coroflot.com/design-jobs"


def _parse_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    for card in soup.find_all("div", class_=lambda c: c and "job" in c.lower()):
        title_el = card.find("h2") or card.find("h3") or card.find("a", class_=lambda c: c and "title" in (c or "").lower())
        title = title_el.get_text(strip=True) if title_el else ""
        if not title or not is_relevant(title):
            continue

        link_el = card.find("a", href=True)
        url = link_el["href"] if link_el else ""
        if url and not url.startswith("http"):
            url = "https://www.coroflot.com" + url

        company_el = card.find("span", class_=lambda c: c and "company" in (c or "").lower())
        company = company_el.get_text(strip=True) if company_el else ""

        loc_el = card.find("span", class_=lambda c: c and "location" in (c or "").lower())
        location = loc_el.get_text(strip=True) if loc_el else ""
        if not is_location_ok(location):
            continue

        jobs.append(
            build_job(
                title=title,
                company=company,
                location=location,
                url=url,
                source=SOURCE,
            )
        )
    return jobs


def fetch() -> list[dict]:
    seen = set()
    results = []

    for term in SEARCH_TERMS:
        resp = get(BASE_URL, params={"q": term})
        if resp:
            for job in _parse_page(resp.text):
                if job["hash"] not in seen:
                    seen.add(job["hash"])
                    results.append(job)
        sleep_between(1, 3)

    return results
