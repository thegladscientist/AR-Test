import os
import sqlite3
from datetime import datetime, timezone, date

# Optional PostgreSQL support
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import dj_database_url
except ImportError:
    psycopg2 = None
    dj_database_url = None

DATABASE_URL = os.environ.get("DATABASE_URL")
DB_PATH = os.path.join(os.path.dirname(__file__), "jobs.db")


class DBConnection:
    def __init__(self, conn, is_postgres=False):
        self.conn = conn
        self.is_postgres = is_postgres

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()

    def execute(self, sql, params=None):
        # Normalize SQL for Postgres vs SQLite
        if self.is_postgres:
            # SQLite uses ? but psycopg2 uses %s for positional
            # SQLite uses :name but psycopg2 uses %(name)s for named
            if params and isinstance(params, dict):
                import re
                sql = re.sub(r':([a-zA-Z0-9_]+)', r'%(\1)s', sql)
            elif params:
                sql = sql.replace('?', '%s')
            
            # Conflict handling
            sql = sql.replace("INSERT OR IGNORE", "INSERT")
            if "INSERT" in sql.upper() and "ON CONFLICT" not in sql.upper():
                sql += " ON CONFLICT (hash) DO NOTHING"
                
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(sql, params)
            return cur
        else:
            # SQLite handles :name and ? natively
            # But we might have added Postgres ON CONFLICT syntax in a generic call
            if "ON CONFLICT" in sql.upper():
                sql = sql.split("ON CONFLICT")[0].replace("INSERT", "INSERT OR IGNORE")
                
            self.conn.row_factory = sqlite3.Row
            cur = self.conn.cursor()
            cur.execute(sql, params or [])
            return cur

    def executescript(self, sql):
        if self.is_postgres:
            # Postgres doesn't have executescript, just run it
            # Also normalize INTEGER PRIMARY KEY AUTOINCREMENT -> SERIAL
            sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
            sql = sql.replace("INSERT OR IGNORE", "INSERT")
            cur = self.conn.cursor()
            cur.execute(sql)
        else:
            self.conn.executescript(sql)


def get_conn():
    if DATABASE_URL:
        # Use Postgres
        if not psycopg2:
            raise ImportError("psycopg2 is required for DATABASE_URL")
        conn = psycopg2.connect(DATABASE_URL)
        return DBConnection(conn, is_postgres=True)
    else:
        # Use SQLite
        conn = sqlite3.connect(DB_PATH)
        return DBConnection(conn, is_postgres=False)


def init_db():
    with get_conn() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id          SERIAL PRIMARY KEY,
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
                id            SERIAL PRIMARY KEY,
                fetched_at    TEXT NOT NULL,
                new_jobs      INTEGER NOT NULL DEFAULT 0,
                sources_ok    TEXT,
                sources_failed TEXT
            );
        """)


def insert_job(job: dict) -> bool:
    """Insert a job; return True if it was new, False if duplicate."""
    with get_conn() as db:
        cur = db.execute(
            """
            INSERT INTO jobs (hash, title, company, location, salary,
                              description, url, source, date_posted, date_fetched)
            VALUES (:hash, :title, :company, :location, :salary,
                    :description, :url, :source, :date_posted, :date_fetched)
            """,
            job,
        )
        return cur.rowcount > 0


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
    params = {}

    if source:
        conditions.append("source = :source")
        params["source"] = source
    if date_from:
        conditions.append("date_fetched >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conditions.append("date_fetched <= :date_to")
        params["date_to"] = date_to
    if favorites_only:
        conditions.append("is_favorited = 1")
    if keyword:
        conditions.append("(title LIKE :kw OR company LIKE :kw OR description LIKE :kw)")
        params["kw"] = f"%{keyword}%"

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * limit

    with get_conn() as db:
        rows = db.execute(
            f"""
            SELECT * FROM jobs
            {where}
            ORDER BY date_fetched DESC, id DESC
            LIMIT :limit OFFSET :offset
            """,
            {**params, "limit": limit, "offset": offset},
        ).fetchall()
        
        total_row = db.execute(
            f"SELECT COUNT(*) FROM jobs {where}", params
        ).fetchone()
        
        # Postgres Row vs SQLite Row access
        if db.is_postgres:
            total = total_row['count'] if total_row else 0
        else:
            total = total_row[0] if total_row else 0

    return [dict(r) for r in rows], total


def get_job_by_id(job_id: int):
    with get_conn() as db:
        row = db.execute("SELECT * FROM jobs WHERE id = :id", {"id": job_id}).fetchone()
    return dict(row) if row else None


def toggle_favorite(job_id: int) -> bool:
    """Toggle favorite flag; return the new value."""
    with get_conn() as db:
        db.execute(
            "UPDATE jobs SET is_favorited = 1 - is_favorited WHERE id = :id",
            {"id": job_id},
        )
        row = db.execute(
            "SELECT is_favorited FROM jobs WHERE id = :id", {"id": job_id}
        ).fetchone()
    
    if not row:
        return False
    return bool(row['is_favorited'])


def log_fetch(new_jobs: int, sources_ok: list, sources_failed: list):
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as db:
        db.execute(
            """
            INSERT INTO fetch_log (fetched_at, new_jobs, sources_ok, sources_failed)
            VALUES (:now, :new_jobs, :sources_ok, :sources_failed)
            """,
            {
                "now": now, 
                "new_jobs": new_jobs, 
                "sources_ok": ",".join(sources_ok), 
                "sources_failed": ",".join(sources_failed)
            },
        )


def get_last_fetch():
    with get_conn() as db:
        row = db.execute(
            "SELECT * FROM fetch_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


def count_new_today():
    today = date.today().isoformat()
    with get_conn() as db:
        row = db.execute(
            "SELECT COUNT(*) FROM jobs WHERE date_fetched >= :today", {"today": today}
        ).fetchone()
    
    if not row:
        return 0
    return row['count'] if hasattr(row, '__getitem__') and 'count' in row.keys() else row[0]


def get_sources():
    with get_conn() as db:
        rows = db.execute(
            "SELECT DISTINCT source FROM jobs ORDER BY source"
        ).fetchall()
    return [r["source"] for r in rows]
