"""
Orchestrates all scrapers and persists results to the DB.
Called by APScheduler daily and also on-demand via /api/fetch.
"""
import logging

from database import insert_job, log_fetch

logger = logging.getLogger(__name__)

# Ordered list of (source_name, fetch_function) pairs
def _get_scrapers():
    from scrapers import (
        remoteok,
        remotive,
        weworkremotely,
        indeed,
        aiga,
        coroflot,
        thedots,
        linkedin,
        wellfound,
        studios,
    )
    return [
        ("RemoteOK",       remoteok.fetch),
        ("Remotive",       remotive.fetch),
        ("WeWorkRemotely", weworkremotely.fetch),
        ("Indeed",         indeed.fetch),
        ("AIGA",           aiga.fetch),
        ("Coroflot",       coroflot.fetch),
        ("TheDots",        thedots.fetch),
        ("LinkedIn",       linkedin.fetch),
        ("Wellfound",      wellfound.fetch),
        ("Studios",        studios.fetch),
    ]


def run_all_scrapers() -> dict:
    """
    Run all scrapers. Returns a summary dict with counts and source status.
    """
    sources_ok = []
    sources_failed = []
    total_new = 0

    for name, fetch_fn in _get_scrapers():
        try:
            jobs = fetch_fn()
            new_count = 0
            for job in jobs:
                if insert_job(job):
                    new_count += 1
            total_new += new_count
            sources_ok.append(name)
            logger.info("%-20s %3d new jobs", name, new_count)
        except Exception as exc:
            sources_failed.append(name)
            logger.warning("%-20s FAILED: %s", name, exc)

    log_fetch(total_new, sources_ok, sources_failed)
    logger.info("Total new jobs this run: %d", total_new)

    return {
        "new_jobs": total_new,
        "sources_ok": sources_ok,
        "sources_failed": sources_failed,
    }
