"""
AIGA Design Jobs — HTML scraper.
https://designjobs.aiga.org/
"""
from bs4 import BeautifulSoup

from .base import build_job, get, is_relevant, is_location_ok, sleep_between

SOURCE = "AIGA Design Jobs"
SEARCH_TERMS = ["creative+director", "creative+technologist", "art+director"]
BASE_URL = "https://designjobs.aiga.org/"


def _parse_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    # AIGA uses a WordPress job board plugin; listings are in <li class="job_listing">
    for card in soup.find_all("li", class_="job_listing"):
        title_el = card.find("h3") or card.find("h2")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title or not is_relevant(title):
            continue

        link_el = card.find("a", href=True)
        url = link_el["href"] if link_el else ""

        company_el = card.find("div", class_="company") or card.find("span", class_="company")
        company = company_el.get_text(strip=True) if company_el else ""

        loc_el = card.find("div", class_="location") or card.find("span", class_="location")
        location = loc_el.get_text(strip=True) if loc_el else ""
        if not is_location_ok(location):
            continue

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

    for term in SEARCH_TERMS:
        resp = get(BASE_URL, params={"s": term.replace("+", " "), "post_type": "job_listing"})
        if resp:
            for job in _parse_page(resp.text):
                if job["hash"] not in seen:
                    seen.add(job["hash"])
                    results.append(job)
        sleep_between(1, 3)

    return results
