"""
Import dmr_monitored_brands.csv into a normalised SQLite database.

The upstream CSV is a fully-denormalised export with one row per BRAND, where
each row repeats its commercial_company / company / holding columns. This
script:

  1. Creates (or replaces) the tables defined in `scripts/dmr_schema.sql`.
  2. Reads the CSV streamingly and deduplicates the four levels by ID.
  3. Seeds the `aliases` table with one row per entity (`source='canonical'`)
     so the alias matcher has something to load on day one. Hand-curated
     OCR/spelling variants can be appended later via separate INSERTs.

Run:
    uv run python scripts/import_dmr_brands.py \
        --csv  dmr_monitored_brands.csv \
        --db   database/dmr.db

The script is idempotent: re-running on the same DB drops and recreates the
DMR tables (it does NOT touch `results.db` or anything else).
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------
#
# This MUST stay in sync with the matcher's runtime normaliser (when that
# lands in src/models/ner/dmr_alias_matcher.py). The contract is:
#
#   normalise(canonical_name) == normalise(ocr_text_substring)
#
# Lossless transforms only here. Anything lossy (e.g. removing legal
# suffixes like "S.p.A.", "Ltd") belongs in additional alias rows so we
# never silently lose the original surface form.

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s&]")  # keep word chars, whitespace, ampersand


def normalise(text: str) -> str:
    """Lowercase, strip accents, collapse punctuation/whitespace."""
    if text is None:
        return ""
    # NFKD splits "é" into "e" + combining acute, which we then drop.
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = _PUNCT_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    return text


def _parse_id(raw: str) -> int:
    """CSV IDs are quoted with thousands separators: '"1,047,623"' → 1047623."""
    return int(raw.replace(",", "").strip())


def _clean_name(raw: str) -> str:
    """Strip surrounding whitespace; preserve case and punctuation for display."""
    return raw.strip()


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

EXPECTED_HEADER = [
    "HOLDING_ID",
    "HOLDING",
    "COMPANY_ID",
    "COMPANY",
    "COMMERCIAL_COMPANY_ID",
    "COMMERCIAL_COMPANY",
    "BRAND_ID",
    "BRAND",
]


def _load_schema(conn: sqlite3.Connection, schema_path: Path) -> None:
    conn.executescript(schema_path.read_text())


def _drop_tables(conn: sqlite3.Connection) -> None:
    # Order matters: children first, then parents, then view.
    conn.executescript("""
        DROP VIEW  IF EXISTS brand_chain;
        DROP TABLE IF EXISTS aliases;
        DROP TABLE IF EXISTS brands;
        DROP TABLE IF EXISTS commercial_companies;
        DROP TABLE IF EXISTS companies;
        DROP TABLE IF EXISTS holdings;
        """)


def _iter_rows(csv_path: Path) -> Iterable[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != EXPECTED_HEADER:
            raise ValueError(
                f"Unexpected CSV header.\n  got:      {reader.fieldnames}\n"
                f"  expected: {EXPECTED_HEADER}"
            )
        yield from reader


def import_csv(csv_path: Path, db_path: Path, schema_path: Path) -> dict[str, int]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        _drop_tables(conn)
        _load_schema(conn, schema_path)

        # In-memory dedupe sets: we only INSERT each ID once.
        seen_holdings: set[int] = set()
        seen_companies: set[int] = set()
        seen_commcos: set[int] = set()
        seen_brands: set[int] = set()

        # Buffered batches for executemany.
        holdings: list[tuple[int, str]] = []
        companies: list[tuple[int, str, int]] = []
        commcos: list[tuple[int, str, int]] = []
        brands: list[tuple[int, str, int]] = []
        aliases: list[tuple[str, int, str, str, str]] = []

        for row in _iter_rows(csv_path):
            h_id = _parse_id(row["HOLDING_ID"])
            c_id = _parse_id(row["COMPANY_ID"])
            cc_id = _parse_id(row["COMMERCIAL_COMPANY_ID"])
            b_id = _parse_id(row["BRAND_ID"])

            h_name = _clean_name(row["HOLDING"])
            c_name = _clean_name(row["COMPANY"])
            cc_name = _clean_name(row["COMMERCIAL_COMPANY"])
            b_name = _clean_name(row["BRAND"])

            if h_id not in seen_holdings:
                seen_holdings.add(h_id)
                holdings.append((h_id, h_name))
                aliases.append(
                    ("HOLDING", h_id, h_name, normalise(h_name), "canonical")
                )

            if c_id not in seen_companies:
                seen_companies.add(c_id)
                companies.append((c_id, c_name, h_id))
                aliases.append(
                    ("COMPANY", c_id, c_name, normalise(c_name), "canonical")
                )

            if cc_id not in seen_commcos:
                seen_commcos.add(cc_id)
                commcos.append((cc_id, cc_name, c_id))
                aliases.append(
                    (
                        "COMMERCIAL_COMPANY",
                        cc_id,
                        cc_name,
                        normalise(cc_name),
                        "canonical",
                    )
                )

            if b_id not in seen_brands:
                seen_brands.add(b_id)
                brands.append((b_id, b_name, cc_id))
                aliases.append(("BRAND", b_id, b_name, normalise(b_name), "canonical"))

        # Bulk insert in dependency order.
        with conn:
            conn.executemany("INSERT INTO holdings (id, name) VALUES (?, ?)", holdings)
            conn.executemany(
                "INSERT INTO companies (id, name, holding_id) VALUES (?, ?, ?)",
                companies,
            )
            conn.executemany(
                "INSERT INTO commercial_companies (id, name, company_id) "
                "VALUES (?, ?, ?)",
                commcos,
            )
            conn.executemany(
                "INSERT INTO brands (id, name, commercial_company_id) "
                "VALUES (?, ?, ?)",
                brands,
            )
            # Aliases: a single entity may share a normalised form with itself
            # across runs of this script; the UNIQUE constraint will reject
            # duplicates, so use OR IGNORE for safety.
            conn.executemany(
                "INSERT OR IGNORE INTO aliases "
                "(entity_type, entity_id, alias_raw, alias_norm, source) "
                "VALUES (?, ?, ?, ?, ?)",
                aliases,
            )

        return {
            "holdings": len(holdings),
            "companies": len(companies),
            "commercial_companies": len(commcos),
            "brands": len(brands),
            "aliases": len(aliases),
        }
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, default=Path("dmr_monitored_brands.csv"))
    p.add_argument("--db", type=Path, default=Path("database/dmr.db"))
    p.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).resolve().parent / "dmr_schema.sql",
    )
    args = p.parse_args(argv)

    if not args.csv.exists():
        print(f"CSV not found: {args.csv}", file=sys.stderr)
        return 1
    if not args.schema.exists():
        print(f"Schema not found: {args.schema}", file=sys.stderr)
        return 1

    counts = import_csv(args.csv, args.db, args.schema)
    print(f"Imported into {args.db}:")
    for k, v in counts.items():
        print(f"  {k:>22s}: {v:>8d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
