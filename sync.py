"""
Sync Script: Runs all scrapers locally and pushes results directly to the Cloud DB (Neon).
Usage: Set DATABASE_URL in your environment first.
"""
import os
import logging
import database as db
import scheduler as sched

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
)
logger = logging.getLogger("SyncTool")

def run_sync():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment!")
        logger.info("Please set it first: $env:DATABASE_URL='postgresql://...' (Windows)")
        return

    logger.info("Connecting to Cloud Database...")
    try:
        db.init_db()
        logger.info("Database initialized (Tables checked/created).")
    except Exception as e:
        logger.error(f"Failed to connect to Neon: {e}")
        return

    logger.info("Starting local scrape (pushing to Cloud)...")
    result = sched.run_all_scrapers()
    
    logger.info("--------------------------------------------------")
    logger.info(f"Sync Complete!")
    logger.info(f"New Jobs Pushed: {result['new_jobs']}")
    logger.info(f"Sources OK: {len(result['sources_ok'])}")
    if result['sources_failed']:
        logger.warning(f"Sources Failed: {result['sources_failed']}")
    logger.info("--------------------------------------------------")

if __name__ == "__main__":
    run_sync()
