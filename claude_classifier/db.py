"""SQLite tracking for pass 1 batches and pass 2 runs.

JSON page files on disk are the source of truth for analysis content; this DB
only mirrors orchestration state (which batch is in flight, which pages
succeeded). Failures here must not abort the pipeline.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from claude_classifier.config import RUNS_DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS pass1_batches (
    run_id           TEXT PRIMARY KEY,
    input_path       TEXT NOT NULL,
    publication_name TEXT,
    issue_date       TEXT,
    country          TEXT,
    batch_id         TEXT NOT NULL,
    model            TEXT NOT NULL,
    page_count       INTEGER NOT NULL,
    submitted_at     TEXT NOT NULL,
    collected_at     TEXT,
    status           TEXT NOT NULL,
    error_message    TEXT,
    pages_succeeded  INTEGER,
    pages_failed     INTEGER
);

CREATE TABLE IF NOT EXISTS pass1_page_results (
    run_id            TEXT NOT NULL,
    image_id          TEXT NOT NULL,
    custom_request_id TEXT NOT NULL,
    sequence_index    INTEGER NOT NULL,
    status            TEXT NOT NULL,
    error_message     TEXT,
    PRIMARY KEY (run_id, image_id),
    FOREIGN KEY (run_id) REFERENCES pass1_batches(run_id)
);

CREATE TABLE IF NOT EXISTS pass2_runs (
    pass2_run_id        TEXT PRIMARY KEY,
    run_id              TEXT NOT NULL,
    started_at          TEXT NOT NULL,
    completed_at        TEXT,
    status              TEXT NOT NULL,
    model               TEXT NOT NULL,
    chunk_count         INTEGER,
    error_message       TEXT,
    FOREIGN KEY (run_id) REFERENCES pass1_batches(run_id)
);
"""

# Additive columns for cost tracking. ``ALTER TABLE ... ADD COLUMN`` is
# idempotent here because we catch the resulting ``duplicate column`` error.
_COST_COLUMNS = (
    ("pass1_batches", "input_tokens INTEGER"),
    ("pass1_batches", "output_tokens INTEGER"),
    ("pass1_batches", "cache_creation_input_tokens INTEGER"),
    ("pass1_batches", "cache_read_input_tokens INTEGER"),
    ("pass1_batches", "cost_usd REAL"),
    ("pass1_batches", "batch_discount INTEGER"),
    ("pass2_runs", "input_tokens INTEGER"),
    ("pass2_runs", "output_tokens INTEGER"),
    ("pass2_runs", "cache_creation_input_tokens INTEGER"),
    ("pass2_runs", "cache_read_input_tokens INTEGER"),
    ("pass2_runs", "cost_usd REAL"),
)


def _apply_cost_columns(conn: sqlite3.Connection) -> None:
    for table, decl in _COST_COLUMNS:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {decl}")
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                raise


@contextmanager
def connect(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = Path(db_path) if db_path else RUNS_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        _apply_cost_columns(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


def insert_pass1_batch(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    input_path: str,
    publication_name: str | None,
    issue_date: str | None,
    country: str | None,
    batch_id: str,
    model: str,
    page_count: int,
    submitted_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO pass1_batches (run_id, input_path, publication_name,
            issue_date, country, batch_id, model, page_count, submitted_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'submitted')
        """,
        (
            run_id,
            input_path,
            publication_name,
            issue_date,
            country,
            batch_id,
            model,
            page_count,
            submitted_at,
        ),
    )


def get_pass1_batch(conn: sqlite3.Connection, run_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM pass1_batches WHERE run_id = ?", (run_id,)
    ).fetchone()


def update_pass1_batch_status(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    status: str,
    collected_at: str | None = None,
    pages_succeeded: int | None = None,
    pages_failed: int | None = None,
    error_message: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE pass1_batches
           SET status = ?, collected_at = COALESCE(?, collected_at),
               pages_succeeded = COALESCE(?, pages_succeeded),
               pages_failed = COALESCE(?, pages_failed),
               error_message = COALESCE(?, error_message)
         WHERE run_id = ?
        """,
        (status, collected_at, pages_succeeded, pages_failed, error_message, run_id),
    )


def insert_pass1_page_result(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    image_id: str,
    custom_request_id: str,
    sequence_index: int,
    status: str,
    error_message: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO pass1_page_results
            (run_id, image_id, custom_request_id, sequence_index, status, error_message)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (run_id, image_id, custom_request_id, sequence_index, status, error_message),
    )


def insert_pass2_run(
    conn: sqlite3.Connection,
    *,
    pass2_run_id: str,
    run_id: str,
    started_at: str,
    model: str,
) -> None:
    conn.execute(
        """
        INSERT INTO pass2_runs (pass2_run_id, run_id, started_at, status, model)
        VALUES (?, ?, ?, 'in_progress', ?)
        """,
        (pass2_run_id, run_id, started_at, model),
    )


def update_pass2_run_status(
    conn: sqlite3.Connection,
    *,
    pass2_run_id: str,
    status: str,
    completed_at: str | None = None,
    chunk_count: int | None = None,
    error_message: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE pass2_runs
           SET status = ?, completed_at = COALESCE(?, completed_at),
               chunk_count = COALESCE(?, chunk_count),
               error_message = COALESCE(?, error_message)
         WHERE pass2_run_id = ?
        """,
        (status, completed_at, chunk_count, error_message, pass2_run_id),
    )


def update_pass1_batch_cost(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_input_tokens: int,
    cache_read_input_tokens: int,
    cost_usd: float,
    batch_discount: bool,
) -> None:
    conn.execute(
        """
        UPDATE pass1_batches
           SET input_tokens = ?, output_tokens = ?,
               cache_creation_input_tokens = ?, cache_read_input_tokens = ?,
               cost_usd = ?, batch_discount = ?
         WHERE run_id = ?
        """,
        (
            input_tokens,
            output_tokens,
            cache_creation_input_tokens,
            cache_read_input_tokens,
            cost_usd,
            1 if batch_discount else 0,
            run_id,
        ),
    )


def update_pass2_run_cost(
    conn: sqlite3.Connection,
    *,
    pass2_run_id: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_input_tokens: int,
    cache_read_input_tokens: int,
    cost_usd: float,
) -> None:
    conn.execute(
        """
        UPDATE pass2_runs
           SET input_tokens = ?, output_tokens = ?,
               cache_creation_input_tokens = ?, cache_read_input_tokens = ?,
               cost_usd = ?
         WHERE pass2_run_id = ?
        """,
        (
            input_tokens,
            output_tokens,
            cache_creation_input_tokens,
            cache_read_input_tokens,
            cost_usd,
            pass2_run_id,
        ),
    )


def list_runs(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("""
        SELECT b.run_id, b.publication_name, b.issue_date, b.country,
               b.status AS pass1_status, b.page_count, b.submitted_at,
               b.collected_at,
               b.cost_usd AS pass1_cost_usd,
               (SELECT COUNT(*) FROM pass2_runs p WHERE p.run_id = b.run_id)
                   AS pass2_run_count,
               (SELECT MAX(started_at) FROM pass2_runs p WHERE p.run_id = b.run_id)
                   AS pass2_latest_at,
               (SELECT COALESCE(SUM(cost_usd), 0) FROM pass2_runs p
                  WHERE p.run_id = b.run_id) AS pass2_cost_usd_total
          FROM pass1_batches b
      ORDER BY b.submitted_at DESC
        """).fetchall()
