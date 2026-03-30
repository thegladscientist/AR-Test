"""
We Work Remotely — RSS feed scraper (using stdlib xml.etree.ElementTree).
Design & Creative category RSS.
"""
import xml.etree.ElementTree as ET

from .base import build_job, get, is_relevant, make_hash, sleep_between

SOURCE = "WeWorkRemotely"

RSS_FEEDS = [
    "https://weworkremotely.com/categories/remote-design-jobs.rss",
    "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
]


def _parse_feed(xml_text: str) -> list[dict]:
    jobs = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return jobs

    ns = {"atom": "http://www.w3.org/2005/Atom"}

    for item in root.iter("item"):
        raw_title = (item.findtext("title") or "").strip()
        url = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or "").strip()

        # Strip simple HTML from description
        try:
            from bs4 import BeautifulSoup
            description = BeautifulSoup(description, "lxml").get_text(" ", strip=True)
        except Exception:
            pass

        # WWR titles are often "Company: Job Title" format
        company = ""
        title = raw_title
        if ": " in raw_title:
            parts = raw_title.split(": ", 1)
            company, title = parts[0].strip(), parts[1].strip()

        if not title or not is_relevant(title):
            continue

        date_posted = (item.findtext("pubDate") or "").strip()
        region_el = item.find("region")
        location = (region_el.text or "Remote") if region_el is not None else "Remote"

        jobs.append(
            build_job(
                title=title,
                company=company,
                location=location,
                url=url,
                source=SOURCE,
                description=description,
                date_posted=date_posted,
            )
        )
    return jobs


def fetch() -> list[dict]:
    seen = set()
    results = []

    for feed_url in RSS_FEEDS:
        resp = get(feed_url)
        if resp:
            for job in _parse_feed(resp.text):
                if job["hash"] not in seen:
                    seen.add(job["hash"])
                    results.append(job)
        sleep_between(1, 2)

    return results
