"""
Wellfound (AngelList Talent) — HTML scraper.
https://wellfound.com/jobs
"""
from bs4 import BeautifulSoup

from .base import build_job, get, is_relevant, is_location_ok, sleep_between

SOURCE = "Wellfound"
BASE_URL = "https://wellfound.com/role/r/creative-director"

ROLE_URLS = [
    "https://wellfound.com/role/r/creative-director",
    "https://wellfound.com/role/r/art-director",
]


def _parse_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    for card in soup.find_all("div", attrs={"data-test": "StartupResult"}):
        title_el = card.find("a", class_=lambda c: c and "job-name" in (c or "").lower())
        if not title_el:
            title_el = card.find("h2") or card.find("h3")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title or not is_relevant(title):
            continue

        company_el = card.find("h2", class_=lambda c: c and "startup-link" in (c or "").lower())
        if not company_el:
            company_el = card.find("a", class_=lambda c: c and "startup" in (c or "").lower())
        company = company_el.get_text(strip=True) if company_el else ""

        link_el = title_el if title_el and title_el.name == "a" else card.find("a", href=True)
        url = link_el.get("href", "") if link_el else ""
        if url and not url.startswith("http"):
            url = "https://wellfound.com" + url

        loc_el = card.find("span", class_=lambda c: c and "location" in (c or "").lower())
        location = loc_el.get_text(strip=True) if loc_el else "Remote"
        if not is_location_ok(location):
            continue

        sal_el = card.find("span", class_=lambda c: c and "salary" in (c or "").lower())
        salary = sal_el.get_text(strip=True) if sal_el else ""

        jobs.append(
            build_job(
                title=title,
                company=company,
                location=location,
                url=url,
                source=SOURCE,
                salary=salary,
            )
        )
    return jobs


def fetch() -> list[dict]:
    seen = set()
    results = []

    for url in ROLE_URLS:
        resp = get(url)
        if resp:
            for job in _parse_page(resp.text):
                if job["hash"] not in seen:
                    seen.add(job["hash"])
                    results.append(job)
        sleep_between(2, 4)

    return results
