"""
Creative Director Job Finder — Flask application.
Run:  python app.py
      http://localhost:5000
"""
import logging
import os
from datetime import datetime, date, timezone, timedelta

from flask import Flask, jsonify, request, send_from_directory, Response

import database as db
import scheduler as sched

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static", static_url_path="")

# ---------------------------------------------------------------------------
# Startup: init DB and schedule daily scrape
# ---------------------------------------------------------------------------
db.init_db()

FETCH_HOUR = int(os.environ.get("FETCH_HOUR", "8"))

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        sched.run_all_scrapers,
        CronTrigger(hour=FETCH_HOUR, minute=0),
        id="daily_fetch",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started — daily fetch at %02d:00", FETCH_HOUR)
except Exception as exc:
    logger.warning("APScheduler not available: %s", exc)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/jobs")
def api_get_jobs():
    source       = request.args.get("source")
    date_from    = request.args.get("date_from")
    date_to      = request.args.get("date_to")
    favorites    = request.args.get("favorites", "").lower() in ("1", "true")
    keyword      = request.args.get("q")
    page         = max(1, int(request.args.get("page", 1)))
    limit        = min(100, max(1, int(request.args.get("limit", 50))))

    jobs, total = db.get_jobs(
        source=source,
        date_from=date_from,
        date_to=date_to,
        favorites_only=favorites,
        keyword=keyword,
        page=page,
        limit=limit,
    )
    return jsonify({"jobs": jobs, "total": total, "page": page, "limit": limit})


@app.post("/api/jobs/<int:job_id>/favorite")
def api_toggle_favorite(job_id: int):
    new_val = db.toggle_favorite(job_id)
    return jsonify({"id": job_id, "is_favorited": new_val})


@app.get("/api/jobs/<int:job_id>/ics")
def api_download_ics(job_id: int):
    job = db.get_job_by_id(job_id)
    if not job:
        return jsonify({"error": "not found"}), 404

    try:
        from ics import Calendar, Event
        from ics.grammar.parse import ContentLine

        cal = Calendar()
        event = Event()
        event.name = f"Apply: {job['title']} @ {job['company']}"
        # Suggest deadline = 7 days from today
        deadline = datetime.now(timezone.utc) + timedelta(days=7)
        event.begin = deadline
        event.make_all_day()

        desc_parts = []
        if job.get("description"):
            desc_parts.append(job["description"])
        desc_parts.append(f"Source: {job['source']}")
        desc_parts.append(f"Link: {job['url']}")
        event.description = "\n\n".join(desc_parts)
        event.url = job["url"]

        cal.events.add(event)
        ics_content = cal.serialize()

        return Response(
            ics_content,
            mimetype="text/calendar",
            headers={
                "Content-Disposition": f'attachment; filename="job-{job_id}.ics"'
            },
        )
    except Exception as exc:
        logger.error("ICS generation failed: %s", exc)
        return jsonify({"error": "ics generation failed"}), 500


@app.get("/api/status")
def api_status():
    last = db.get_last_fetch()
    new_today = db.count_new_today()
    sources = db.get_sources()
    return jsonify(
        {
            "last_fetch": last,
            "new_today": new_today,
            "sources": sources,
        }
    )


@app.post("/api/fetch")
def api_trigger_fetch():
    """Manually trigger a scrape run — useful for testing."""
    logger.info("Manual fetch triggered via API")
    result = sched.run_all_scrapers()
    return jsonify(result)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info("Starting on http://localhost:%d", port)
    app.run(host="0.0.0.0", port=port, debug=False)
