"""
Curated studio careers page scrapers.
Each studio has its own parser since pages vary widely.
Returns jobs gracefully if a studio page structure changes.
"""
from bs4 import BeautifulSoup

from .base import build_job, get, is_relevant, is_location_ok, sleep_between

SOURCE = "Studio"

STUDIOS = [
    {
        "name": "IDEO",
        "url": "https://www.ideo.com/careers",
        "list_selector": "a",
        "title_selector": None,
    },
    {
        "name": "R/GA",
        "url": "https://www.rga.com/careers",
        "list_selector": "li",
        "title_selector": "h3",
    },
    {
        "name": "Huge",
        "url": "https://www.hugeinc.com/careers",
        "list_selector": "li",
        "title_selector": "h3",
    },
    {
        "name": "MediaMonks",
        "url": "https://monks.com/careers",
        "list_selector": "li",
        "title_selector": "h3",
    },
    {
        "name": "Fantasy",
        "url": "https://fantasy.co/careers",
        "list_selector": "li",
        "title_selector": "h3",
    },
    {
        "name": "Instrument",
        "url": "https://instrument.com/careers",
        "list_selector": "li",
        "title_selector": "h3",
    },
    {
        "name": "Wieden+Kennedy",
        "url": "https://www.wk.com/work/join-us",
        "list_selector": "li",
        "title_selector": "h3",
    },
]


def _parse_studio(html: str, studio: dict) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    jobs = []
    name = studio["name"]
    page_url = studio["url"]

    # Generic heuristic: find all text that looks like a job title
    for el in soup.find_all(["h2", "h3", "h4", "li", "a"]):
        text = el.get_text(strip=True)
        if not text or len(text) > 120 or len(text) < 5:
            continue
        if not is_relevant(text):
            continue

        # Try to get a URL for this job
        link = el.find("a") if el.name != "a" else el
        url = ""
        if link and link.get("href"):
            url = link["href"]
            if not url.startswith("http"):
                from urllib.parse import urljoin
                url = urljoin(page_url, url)
        if not url:
            url = page_url

        # Location: look for sibling/parent text mentioning location
        location = "Remote"
        parent_text = (el.parent.get_text(" ", strip=True) if el.parent else "").lower()
        if "barcelona" in parent_text:
            location = "Barcelona"
        elif "remote" in parent_text or "anywhere" in parent_text:
            location = "Remote"

        jobs.append(
            build_job(
                title=text,
                company=name,
                location=location,
                url=url,
                source=f"{SOURCE} ({name})",
            )
        )

    return jobs


def fetch() -> list[dict]:
    seen = set()
    results = []

    for studio in STUDIOS:
        resp = get(studio["url"])
        if resp:
            for job in _parse_studio(resp.text, studio):
                if job["hash"] not in seen:
                    seen.add(job["hash"])
                    results.append(job)
        sleep_between(1, 3)

    return results
