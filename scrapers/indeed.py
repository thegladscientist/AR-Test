"""
Indeed — HTML scraper.
Searches for creative director / art director roles (remote + Barcelona).
"""
from bs4 import BeautifulSoup

from .base import build_job, get, is_relevant, is_location_ok, sleep_between

SOURCE = "Indeed"

SEARCH_CONFIGS = [
    {"q": "creative director", "l": "Remote", "remotejob": "1"},
    {"q": "creative technologist", "l": "Remote", "remotejob": "1"},
    {"q": "senior art director", "l": "Remote", "remotejob": "1"},
    {"q": "creative director", "l": "Barcelona, Spain"},
]

BASE_URL = "https://www.indeed.com/jobs"


def _parse_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    # Indeed job cards use data-jk attribute
    cards = soup.find_all("div", attrs={"data-jk": True})
    for card in cards:
        title_el = card.find("h2", class_=lambda c: c and "jobTitle" in c)
        title = title_el.get_text(strip=True) if title_el else ""
        if not title or not is_relevant(title):
            continue

        company_el = card.find("span", attrs={"data-testid": "company-name"})
        if not company_el:
            company_el = card.find("span", class_=lambda c: c and "companyName" in c)
        company = company_el.get_text(strip=True) if company_el else ""

        loc_el = card.find("div", attrs={"data-testid": "text-location"})
        location = loc_el.get_text(strip=True) if loc_el else ""

        if not is_location_ok(location):
            continue

        jk = card.get("data-jk", "")
        url = f"https://www.indeed.com/viewjob?jk={jk}" if jk else ""
        if not url:
            continue

        salary_el = card.find("div", attrs={"data-testid": "attribute_snippet_testid"})
        salary = salary_el.get_text(strip=True) if salary_el else ""

        desc_el = card.find("div", class_=lambda c: c and "job-snippet" in (c or ""))
        description = desc_el.get_text(" ", strip=True) if desc_el else ""

        jobs.append(
            build_job(
                title=title,
                company=company,
                location=location,
                url=url,
                source=SOURCE,
                description=description,
                salary=salary,
            )
        )
    return jobs


def fetch() -> list[dict]:
    seen = set()
    results = []

    for config in SEARCH_CONFIGS:
        for offset in [0, 10, 20, 30]:
            params = config.copy()
            params["start"] = str(offset)
            resp = get(BASE_URL, params=params)
            if resp:
                jobs = _parse_page(resp.text)
                for job in jobs:
                    if job["hash"] not in seen:
                        seen.add(job["hash"])
                        results.append(job)
                if not jobs:
                    break
            sleep_between(2, 4)

    return results
