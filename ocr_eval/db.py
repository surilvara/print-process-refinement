"""SQLite store for OCR comparison results.

Schema:
- runs            One row per evaluation invocation (orchestrator or compare.py).
- comparisons     One row per (run_id, runner, image_stem). FK → runs.run_id.
- run_failures    OCR-stage failures captured by the orchestrator. FK → runs.run_id.

Every invocation generates a single `run_id` (UTC timestamp string) so the
same evaluation across multiple runners is grouped. Inserts are best-effort:
failures are logged to stderr and never raise. JSON/CSV remain the source
of truth.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from metrics import ComparisonRow
from paths import DEFAULT_DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id        TEXT PRIMARY KEY,
    started_at    TEXT NOT NULL,
    input_path    TEXT,
    runners       TEXT,          -- comma-separated runner names that participated
    skipped_ocr   INTEGER NOT NULL DEFAULT 0,
    notes         TEXT
);

CREATE TABLE IF NOT EXISTS comparisons (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id              TEXT,
    run_timestamp       TEXT NOT NULL,    -- kept for back-compat; equals run_id
    runner              TEXT NOT NULL,
    image_stem          TEXT NOT NULL,
    cer                 REAL NOT NULL,
    wer                 REAL NOT NULL,
    ref_block_count     INTEGER NOT NULL,
    hyp_block_count     INTEGER NOT NULL,
    mean_iou            REAL NOT NULL,
    ref_chars           INTEGER NOT NULL,
    hyp_chars           INTEGER NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_comparisons_runner_ts
    ON comparisons (runner, run_timestamp);

CREATE INDEX IF NOT EXISTS idx_comparisons_run_id
    ON comparisons (run_id);

CREATE INDEX IF NOT EXISTS idx_comparisons_image
    ON comparisons (image_stem);

CREATE TABLE IF NOT EXISTS run_failures (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL,
    runner          TEXT NOT NULL,
    image_stem      TEXT,          -- NULL if failure was runner-wide (no .venv, etc.)
    stage           TEXT NOT NULL, -- 'ocr' | 'compare'
    error_message   TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_run_failures_run_id
    ON run_failures (run_id);

CREATE TABLE IF NOT EXISTS ocr_runs (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id             TEXT NOT NULL,
    runner             TEXT NOT NULL,
    started_at         TEXT NOT NULL,
    ended_at           TEXT NOT NULL,
    duration_seconds   REAL NOT NULL,
    image_count        INTEGER NOT NULL,
    exit_code          INTEGER NOT NULL,
    output_dir         TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_ocr_runs_run_id
    ON ocr_runs (run_id);

CREATE INDEX IF NOT EXISTS idx_ocr_runs_runner
    ON ocr_runs (runner);
"""

# Recreated each connect to pick up schema changes.
_VIEWS = """
DROP VIEW IF EXISTS latest_comparison;
CREATE VIEW latest_comparison AS
SELECT c.*
FROM comparisons c
JOIN (
    SELECT runner, MAX(run_timestamp) AS max_ts
    FROM comparisons
    GROUP BY runner
) latest
  ON c.runner = latest.runner
 AND c.run_timestamp = latest.max_ts;
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA)
    # Migration: add run_id column to pre-existing comparisons tables.
    cols = {row[1] for row in conn.execute("PRAGMA table_info(comparisons)")}
    if "run_id" not in cols:
        conn.execute("ALTER TABLE comparisons ADD COLUMN run_id TEXT")
        conn.execute(
            "UPDATE comparisons SET run_id = run_timestamp WHERE run_id IS NULL"
        )
    conn.executescript(_VIEWS)
    return conn


def new_run_id() -> str:
    """Generate a UTC timestamp string suitable for use as a run_id."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def insert_run_record(
    run_id: str,
    input_path: str | None,
    runners: list[str],
    skipped_ocr: bool,
    notes: str | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> bool:
    """Insert (or replace) a row in the `runs` table."""
    try:
        conn = _connect(db_path)
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO runs
                  (run_id, started_at, input_path, runners, skipped_ocr, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    datetime.now(timezone.utc).isoformat(),
                    input_path,
                    ",".join(runners) if runners else None,
                    1 if skipped_ocr else 0,
                    notes,
                ),
            )
        conn.close()
        return True
    except Exception as exc:  # noqa: BLE001 - DB is best-effort
        print(f"warning: failed to write run record: {exc}", file=sys.stderr)
        return False


def insert_failures(
    run_id: str,
    failures: list[tuple[str, str | None, str, str]],
    db_path: Path = DEFAULT_DB_PATH,
) -> bool:
    """Insert OCR/compare failures for a run.

    `failures` is a list of (runner, image_stem_or_None, stage, error_message).
    """
    if not failures:
        return True
    try:
        conn = _connect(db_path)
        with conn:
            conn.executemany(
                """
                INSERT INTO run_failures
                  (run_id, runner, image_stem, stage, error_message)
                VALUES (?, ?, ?, ?, ?)
                """,
                [(run_id, r, s, stage, msg) for (r, s, stage, msg) in failures],
            )
        conn.close()
        return True
    except Exception as exc:  # noqa: BLE001 - DB is best-effort
        print(f"warning: failed to write run failures: {exc}", file=sys.stderr)
        return False


def insert_run(
    rows: list[ComparisonRow],
    db_path: Path = DEFAULT_DB_PATH,
    run_timestamp: str | None = None,
    run_id: str | None = None,
) -> str | None:
    """Insert a batch of comparison rows. Returns the run_id used,
    or None on failure.

    If `run_id` is None, a fresh one is generated (back-compat for callers
    that don't yet thread a shared run_id).
    """
    if not rows:
        return None
    rid = run_id or run_timestamp or new_run_id()
    try:
        conn = _connect(db_path)
        with conn:
            conn.executemany(
                """
                INSERT INTO comparisons (
                    run_id, run_timestamp, runner, image_stem,
                    cer, wer,
                    ref_block_count, hyp_block_count,
                    mean_iou, ref_chars, hyp_chars
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        rid,
                        rid,
                        r.runner,
                        r.image_stem,
                        r.cer,
                        r.wer,
                        r.ref_block_count,
                        r.hyp_block_count,
                        r.mean_iou,
                        r.ref_chars,
                        r.hyp_chars,
                    )
                    for r in rows
                ],
            )
        conn.close()
        return rid
    except Exception as exc:  # noqa: BLE001 - DB is best-effort
        print(f"warning: failed to write comparison DB: {exc}", file=sys.stderr)
        return None


def insert_ocr_run(
    run_id: str,
    runner: str,
    started_at: str,
    ended_at: str,
    duration_seconds: float,
    image_count: int,
    exit_code: int,
    output_dir: str | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> bool:
    """Insert a per-runner OCR execution record.

    Tracks wall-clock duration so the UI / standup queries can show how
    long each model took to process a batch.
    """
    try:
        conn = _connect(db_path)
        with conn:
            conn.execute(
                """
                INSERT INTO ocr_runs
                  (run_id, runner, started_at, ended_at, duration_seconds,
                   image_count, exit_code, output_dir)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    runner,
                    started_at,
                    ended_at,
                    duration_seconds,
                    image_count,
                    exit_code,
                    output_dir,
                ),
            )
        conn.close()
        return True
    except Exception as exc:  # noqa: BLE001 - DB is best-effort
        print(f"warning: failed to write ocr_run record: {exc}", file=sys.stderr)
        return False


def fetch_ocr_runs_for_run_id(
    run_id: str, db_path: Path = DEFAULT_DB_PATH
) -> list[dict]:
    """Return all ocr_runs rows for a given `run_id` as plain dicts.

    Best-effort: returns an empty list on any DB error.
    """
    try:
        conn = _connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT runner, started_at, ended_at, duration_seconds,
                   image_count, exit_code, output_dir
            FROM ocr_runs
            WHERE run_id = ?
            ORDER BY started_at
            """,
            (run_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as exc:  # noqa: BLE001 - DB is best-effort
        print(f"warning: failed to read ocr_runs: {exc}", file=sys.stderr)
        return []
