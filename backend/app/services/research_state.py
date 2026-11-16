"""Durable local operational history. Never store credentials or portfolio data."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB = Path(__file__).resolve().parents[3] / ".cache" / "research.sqlite3"


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connection():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=10000")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS refresh_runs (
          id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT,
          status TEXT NOT NULL, details TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS analysis_attempts (
          id TEXT PRIMARY KEY, document_id TEXT NOT NULL, text_sha256 TEXT NOT NULL,
          model TEXT NOT NULL, prompt_version TEXT NOT NULL, started_at TEXT NOT NULL,
          finished_at TEXT, status TEXT NOT NULL, error_code TEXT, http_status INTEGER);
        CREATE TABLE IF NOT EXISTS imported_budget (day TEXT PRIMARY KEY, attempts INTEGER NOT NULL);
    """)
    try:
        with db:
            yield db
    finally:
        db.close()


def start_refresh():
    run_id = str(uuid.uuid4())
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        recent = db.execute("SELECT started_at,status FROM refresh_runs ORDER BY started_at DESC LIMIT 1").fetchone()
        if recent:
            age = (datetime.now(timezone.utc)-datetime.fromisoformat(recent["started_at"])).total_seconds()
            if age < 30 or recent["status"] == "running" and age < 300:
                raise ValueError("A refresh is running or was checked recently. Try again shortly.")
        db.execute("INSERT INTO refresh_runs VALUES (?,?,NULL,'running','{}')", (run_id, now()))
    return run_id


def finish_refresh(run_id, status, details):
    with connection() as db:
        db.execute("UPDATE refresh_runs SET finished_at=?,status=?,details=? WHERE id=?",
                   (now(), status, json.dumps(details), run_id))


def refresh_history(limit=20):
    with connection() as db:
        rows = db.execute("SELECT * FROM refresh_runs ORDER BY started_at DESC LIMIT ?", (max(1,min(limit,100)),)).fetchall()
    return [{**dict(row), "details": json.loads(row["details"])} for row in rows]


def reserve_attempt(document, model, prompt_version, limit):
    """Count every outgoing request atomically, including retries and failures."""
    from ..models.rbi import AnalysisUnavailable
    stamp = now()
    attempt_id = str(uuid.uuid4())
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        legacy = DB.parent / "rbi_analysis" / "budget.json"
        if legacy.exists():
            try:
                budget = json.loads(legacy.read_text(encoding="utf-8"))
                if budget.get("date") == stamp[:10]:
                    db.execute("INSERT OR IGNORE INTO imported_budget VALUES (?,?)", (stamp[:10],max(0,int(budget.get("attempts",0)))))
            except (ValueError,OSError,TypeError):
                raise AnalysisUnavailable("Legacy budget cannot be verified; check local budget storage.",code="budget_unavailable") from None
        used = db.execute("SELECT count(*) FROM analysis_attempts WHERE substr(started_at,1,10)=?", (stamp[:10],)).fetchone()[0]
        previous = db.execute("SELECT attempts FROM imported_budget WHERE day=?",(stamp[:10],)).fetchone()
        used += previous[0] if previous else 0
        if used >= limit:
            raise AnalysisUnavailable("Daily Gemini request budget reached. Cached research remains available.", code="budget_exhausted")
        db.execute("INSERT INTO analysis_attempts VALUES (?,?,?,?,?,?,NULL,'running',NULL,NULL)",
                   (attempt_id, document.id, document.text_sha256, model, prompt_version, stamp))
    return attempt_id


def finish_attempt(attempt_id, status, error_code=None, http_status=None):
    with connection() as db:
        db.execute("UPDATE analysis_attempts SET finished_at=?,status=?,error_code=?,http_status=? WHERE id=?",
                   (now(),status,error_code,http_status,attempt_id))


def analysis_history(limit=20):
    with connection() as db:
        rows = db.execute("SELECT * FROM analysis_attempts ORDER BY started_at DESC LIMIT ?", (max(1,min(limit,200)),)).fetchall()
    return [dict(row) for row in rows]
