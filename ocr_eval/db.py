"""SQLite store for OCR comparison results.

One row per (run_timestamp, runner, image_stem). Each invocation of
compare.py inserts a new batch tagged with the same run_timestamp, so you
can both see history over time and query "latest run per runner".

The DB is best-effort: failure to write is logged to stderr but never
raises. The CSV / stdout outputs remain the source of truth.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from metrics import ComparisonRow
from paths import DEFAULT_DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS comparisons (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_timestamp       TEXT NOT NULL,
    runner              TEXT NOT NULL,
    image_stem          TEXT NOT NULL,
    cer                 REAL NOT NULL,
    wer                 REAL NOT NULL,
    ref_block_count     INTEGER NOT NULL,
    hyp_block_count     INTEGER NOT NULL,
    block_count_delta   INTEGER NOT NULL,
    mean_iou            REAL NOT NULL,
    ref_chars           INTEGER NOT NULL,
    hyp_chars           INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_comparisons_runner_ts
    ON comparisons (runner, run_timestamp);

CREATE INDEX IF NOT EXISTS idx_comparisons_image
    ON comparisons (image_stem);

-- Convenience view: most recent run per runner.
CREATE VIEW IF NOT EXISTS latest_comparison AS
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
    return conn


def insert_run(
    rows: list[ComparisonRow],
    db_path: Path = DEFAULT_DB_PATH,
    run_timestamp: str | None = None,
) -> str | None:
    """Insert a batch of comparison rows. Returns the run_timestamp used,
    or None on failure."""
    if not rows:
        return None
    ts = run_timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        conn = _connect(db_path)
        with conn:
            conn.executemany(
                """
                INSERT INTO comparisons (
                    run_timestamp, runner, image_stem,
                    cer, wer,
                    ref_block_count, hyp_block_count, block_count_delta,
                    mean_iou, ref_chars, hyp_chars
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        ts,
                        r.runner,
                        r.image_stem,
                        r.cer,
                        r.wer,
                        r.ref_block_count,
                        r.hyp_block_count,
                        r.block_count_delta,
                        r.mean_iou,
                        r.ref_chars,
                        r.hyp_chars,
                    )
                    for r in rows
                ],
            )
        conn.close()
        return ts
    except Exception as exc:  # noqa: BLE001 - DB is best-effort
        print(f"warning: failed to write comparison DB: {exc}", file=sys.stderr)
        return None
