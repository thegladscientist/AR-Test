import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "jobs.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                hash        TEXT UNIQUE NOT NULL,
                title       TEXT NOT NULL,
                company     TEXT NOT NULL DEFAULT '',
                location    TEXT NOT NULL DEFAULT '',
                salary      TEXT,
                description TEXT,
                url         TEXT NOT NULL,
                source      TEXT NOT NULL,
                date_posted TEXT,
                date_fetched TEXT NOT NULL,
                is_favorited INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_date_fetched ON jobs(date_fetched);
            CREATE INDEX IF NOT EXISTS idx_jobs_source      ON jobs(source);
            CREATE INDEX IF NOT EXISTS idx_jobs_favorited   ON jobs(is_favorited);

            CREATE TABLE IF NOT EXISTS fetch_log (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                fetched_at    TEXT NOT NULL,
                new_jobs      INTEGER NOT NULL DEFAULT 0,
                sources_ok    TEXT,
                sources_failed TEXT
            );
        """)


def insert_job(job: dict) -> bool:
    """Insert a job; return True if it was new, False if duplicate."""
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO jobs (hash, title, company, location, salary,
                                  description, url, source, date_posted, date_fetched)
                VALUES (:hash, :title, :company, :location, :salary,
                        :description, :url, :source, :date_posted, :date_fetched)
                """,
                job,
            )
        return True
    except sqlite3.IntegrityError:
        return False


def get_jobs(
    source=None,
    date_from=None,
    date_to=None,
    favorites_only=False,
    keyword=None,
    page=1,
    limit=50,
):
    conditions = []
    params = []

    if source:
        conditions.append("source = ?")
        params.append(source)
    if date_from:
        conditions.append("date_fetched >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("date_fetched <= ?")
        params.append(date_to)
    if favorites_only:
        conditions.append("is_favorited = 1")
    if keyword:
        conditions.append("(title LIKE ? OR company LIKE ? OR description LIKE ?)")
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * limit

    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM jobs
            {where}
            ORDER BY date_fetched DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()
        total = conn.execute(
            f"SELECT COUNT(*) FROM jobs {where}", params
        ).fetchone()[0]

    return [dict(r) for r in rows], total


def get_job_by_id(job_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


def toggle_favorite(job_id: int) -> bool:
    """Toggle favorite flag; return the new value."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET is_favorited = 1 - is_favorited WHERE id = ?",
            (job_id,),
        )
        row = conn.execute(
            "SELECT is_favorited FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
    return bool(row["is_favorited"]) if row else False


def log_fetch(new_jobs: int, sources_ok: list, sources_failed: list):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO fetch_log (fetched_at, new_jobs, sources_ok, sources_failed)
            VALUES (?, ?, ?, ?)
            """,
            (now, new_jobs, ",".join(sources_ok), ",".join(sources_failed)),
        )


def get_last_fetch():
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM fetch_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


def count_new_today():
    from datetime import date
    today = date.today().isoformat()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE date_fetched >= ?", (today,)
        ).fetchone()
    return row[0]


def get_sources():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT source FROM jobs ORDER BY source"
        ).fetchall()
    return [r["source"] for r in rows]
