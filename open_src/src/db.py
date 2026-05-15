from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from loguru import logger


SCHEMA = """
CREATE TABLE IF NOT EXISTS publications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    magazine_name TEXT,
    source_path TEXT NOT NULL,
    issue_date TEXT,
    language TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_publications_magazine_name ON publications(magazine_name);
CREATE INDEX IF NOT EXISTS idx_publications_issue_date ON publications(issue_date);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    input_file TEXT NOT NULL,
    processed_at TEXT NOT NULL,
    pipeline_version TEXT NOT NULL,
    ocr_model TEXT NOT NULL,
    layout_model TEXT NOT NULL,
    ner_model TEXT NOT NULL,
    image_analysis_model TEXT NOT NULL,
    total_pages INTEGER NOT NULL,
    output_json_filename TEXT NOT NULL UNIQUE,
    publication_id INTEGER REFERENCES publications(id) ON DELETE SET NULL,
    -- TEXT so non-numeric labels ("iv", "A12", "B3") are storable later
    -- without a migration. Insertion order is preserved by runs.id.
    page_label TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_input_file ON runs(input_file);
CREATE INDEX IF NOT EXISTS idx_runs_processed_at ON runs(processed_at);
CREATE INDEX IF NOT EXISTS idx_runs_publication_id ON runs(publication_id);

CREATE TABLE IF NOT EXISTS run_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    page_number INTEGER,
    message TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_run_errors_run_id ON run_errors(run_id);

CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    -- Heuristic from src.output_handler.classify_page; replaceable by a real
    -- classifier later — column accepts any string.
    classification TEXT,
    classification_reason TEXT,
    UNIQUE (run_id, page_number)
);

CREATE INDEX IF NOT EXISTS idx_pages_classification ON pages(classification);

CREATE TABLE IF NOT EXISTS text_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    block_id TEXT NOT NULL,
    block_type TEXT NOT NULL,
    text TEXT NOT NULL,
    bbox_x_min REAL NOT NULL,
    bbox_y_min REAL NOT NULL,
    bbox_x_max REAL NOT NULL,
    bbox_y_max REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_text_blocks_page_id ON text_blocks(page_id);
CREATE INDEX IF NOT EXISTS idx_text_blocks_block_type ON text_blocks(block_type);

CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text_block_id INTEGER NOT NULL REFERENCES text_blocks(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    label TEXT NOT NULL,
    start_offset INTEGER NOT NULL,
    end_offset INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entities_text_block_id ON entities(text_block_id);
CREATE INDEX IF NOT EXISTS idx_entities_label_text ON entities(label, text);

-- detection bboxes are CROP-relative (relative to the parent image_region.bbox),
-- matching the JSON schema. Compose with the parent region bbox for page coords.
CREATE TABLE IF NOT EXISTS image_regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    region_id TEXT NOT NULL,
    bbox_x_min REAL NOT NULL,
    bbox_y_min REAL NOT NULL,
    bbox_x_max REAL NOT NULL,
    bbox_y_max REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_image_regions_page_id ON image_regions(page_id);

CREATE TABLE IF NOT EXISTS detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_region_id INTEGER NOT NULL REFERENCES image_regions(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    confidence REAL NOT NULL,
    bbox_x_min REAL NOT NULL,
    bbox_y_min REAL NOT NULL,
    bbox_x_max REAL NOT NULL,
    bbox_y_max REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_detections_image_region_id ON detections(image_region_id);
CREATE INDEX IF NOT EXISTS idx_detections_label ON detections(label);
"""


_ERROR_PAGE_RE = re.compile(r"^Page (\d+):\s*(.*)$")


def _parse_error(msg: str) -> tuple[int | None, str]:
    m = _ERROR_PAGE_RE.match(msg)
    if m:
        return int(m.group(1)), m.group(2)
    return None, msg


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _ensure_schema(conn: sqlite3.Connection) -> None:
    # Migration must happen before executescript: the SCHEMA's CREATE INDEX
    # statements reference new columns, so a pre-existing table missing those
    # columns causes the script to fail mid-way.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS publications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            magazine_name TEXT,
            source_path TEXT NOT NULL,
            issue_date TEXT,
            language TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    pub_cols = _column_names(conn, "publications")
    if "magazine_name" not in pub_cols:
        conn.execute("ALTER TABLE publications ADD COLUMN magazine_name TEXT")

    runs_exists = (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='runs'"
        ).fetchone()
        is not None
    )
    if runs_exists:
        runs_cols = _column_names(conn, "runs")
        if "publication_id" not in runs_cols:
            conn.execute(
                "ALTER TABLE runs ADD COLUMN publication_id INTEGER "
                "REFERENCES publications(id) ON DELETE SET NULL"
            )
        if "page_label" not in runs_cols:
            conn.execute("ALTER TABLE runs ADD COLUMN page_label TEXT")

    pages_exists = (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='pages'"
        ).fetchone()
        is not None
    )
    if pages_exists:
        pages_cols = _column_names(conn, "pages")
        if "classification" not in pages_cols:
            conn.execute("ALTER TABLE pages ADD COLUMN classification TEXT")
        if "classification_reason" not in pages_cols:
            conn.execute("ALTER TABLE pages ADD COLUMN classification_reason TEXT")

    conn.executescript(SCHEMA)


def _get_or_create_publication(
    conn: sqlite3.Connection,
    name: str,
    source_path: str,
    created_at: str,
    magazine_name: str | None = None,
    issue_date: str | None = None,
) -> int:
    """Return existing publications.id for `name`, or insert a new row.

    Identity is by `name` (folder basename). Re-running the same publication
    folder reuses the row so all runs accumulate against one publication.
    On reuse, magazine_name and issue_date are NOT overwritten — first-write
    wins, so manual edits in the DB survive subsequent pipeline runs.
    """
    row = conn.execute(
        "SELECT id FROM publications WHERE name = ?", (name,)
    ).fetchone()
    if row is not None:
        return row[0]
    cursor = conn.execute(
        """
        INSERT INTO publications (name, magazine_name, source_path, issue_date, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, magazine_name, source_path, issue_date, created_at),
    )
    return cursor.lastrowid


def insert_run(
    db_path: Path, output_data: dict[str, Any], output_json_filename: str
) -> int | None:
    """Insert one pipeline run plus its child rows. Returns the run id, or None on failure.

    Best-effort: any failure (locked DB, disk full, malformed payload) is logged
    as a warning and swallowed. The JSON output remains the source of truth.
    """
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            _ensure_schema(conn)

            metadata = output_data["metadata"]
            models = metadata["models"]
            document = output_data["document"]
            pages = output_data["pages"]
            errors = output_data["errors"]
            publication = metadata.get("publication")

            with conn:
                publication_id: int | None = None
                page_label: str | None = None
                if publication is not None:
                    publication_id = _get_or_create_publication(
                        conn,
                        name=publication["name"],
                        source_path=publication["source_path"],
                        created_at=metadata["timestamp"],
                        magazine_name=publication.get("magazine_name"),
                        issue_date=publication.get("issue_date"),
                    )
                    page_label = publication.get("page_label")

                cursor = conn.execute(
                    """
                    INSERT INTO runs (
                        input_file, processed_at, pipeline_version,
                        ocr_model, layout_model, ner_model, image_analysis_model,
                        total_pages, output_json_filename,
                        publication_id, page_label
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        metadata["input_file"],
                        metadata["timestamp"],
                        metadata["pipeline_version"],
                        models["ocr"],
                        models["layout"],
                        models["ner"],
                        models["image_analysis"],
                        document["total_pages"],
                        output_json_filename,
                        publication_id,
                        page_label,
                    ),
                )
                run_id = cursor.lastrowid

                for err in errors:
                    page_no, message = _parse_error(err)
                    conn.execute(
                        "INSERT INTO run_errors (run_id, page_number, message) VALUES (?, ?, ?)",
                        (run_id, page_no, message),
                    )

                for page in pages:
                    cursor = conn.execute(
                        """
                        INSERT INTO pages (
                            run_id, page_number, classification, classification_reason
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (
                            run_id,
                            page["page_number"],
                            page.get("classification"),
                            page.get("classification_reason"),
                        ),
                    )
                    page_id = cursor.lastrowid

                    for tb in page["text_blocks"]:
                        bbox = tb["bbox"]
                        cursor = conn.execute(
                            """
                            INSERT INTO text_blocks (
                                page_id, block_id, block_type, text,
                                bbox_x_min, bbox_y_min, bbox_x_max, bbox_y_max
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                page_id,
                                tb["id"],
                                tb["type"],
                                tb["text"],
                                bbox[0],
                                bbox[1],
                                bbox[2],
                                bbox[3],
                            ),
                        )
                        text_block_id = cursor.lastrowid

                        for ent in tb["entities"]:
                            conn.execute(
                                """
                                INSERT INTO entities (
                                    text_block_id, text, label, start_offset, end_offset
                                ) VALUES (?, ?, ?, ?, ?)
                                """,
                                (
                                    text_block_id,
                                    ent["text"],
                                    ent["label"],
                                    ent["start"],
                                    ent["end"],
                                ),
                            )

                    for ir in page["image_regions"]:
                        bbox = ir["bbox"]
                        cursor = conn.execute(
                            """
                            INSERT INTO image_regions (
                                page_id, region_id,
                                bbox_x_min, bbox_y_min, bbox_x_max, bbox_y_max
                            ) VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                page_id,
                                ir["id"],
                                bbox[0],
                                bbox[1],
                                bbox[2],
                                bbox[3],
                            ),
                        )
                        region_db_id = cursor.lastrowid

                        for det in ir["detections"]:
                            dbbox = det["bbox"]
                            conn.execute(
                                """
                                INSERT INTO detections (
                                    image_region_id, label, confidence,
                                    bbox_x_min, bbox_y_min, bbox_x_max, bbox_y_max
                                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    region_db_id,
                                    det["label"],
                                    det["confidence"],
                                    dbbox[0],
                                    dbbox[1],
                                    dbbox[2],
                                    dbbox[3],
                                ),
                            )

            return run_id
        finally:
            conn.close()
    except Exception as e:
        logger.warning(
            f"Failed to record run in database {db_path}: {type(e).__name__}: {e}"
        )
        return None
