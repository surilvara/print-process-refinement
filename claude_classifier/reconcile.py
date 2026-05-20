"""Brand reconciliation: run DMR alias matcher over GoogleVision OCR text per page.

Sits between pass 1 and pass 2 (see Q11 option c). The alias matcher is
authoritative for canonical brand identity; Claude's ``claude_visual`` list is
a parallel signal that pass 2 reads but does not override.

The matcher itself is vendored at ``claude_classifier/dmr_matcher.py`` — this
module just provides a cached singleton and the OCR-text reader.
"""

from __future__ import annotations

import json
from pathlib import Path

from claude_classifier.config import DMR_DB_PATH
from claude_classifier.dmr_matcher import CanonicalBrand, DMRMatcher

_MATCHER: DMRMatcher | None = None


def _get_matcher(db_path: Path = DMR_DB_PATH) -> DMRMatcher:
    global _MATCHER
    if _MATCHER is None:
        m = DMRMatcher(db_path=db_path)
        m.load()
        _MATCHER = m
    return _MATCHER


def load_canonical_brands_for_text(
    text: str, db_path: Path = DMR_DB_PATH
) -> list[CanonicalBrand]:
    """Match aliases against ``text``; return deduped canonical entities."""
    if not text:
        return []
    return _get_matcher(db_path).match(text)


def extract_ocr_text(googlevision_json_path: Path) -> str:
    """Return ``fullTextAnnotation.text`` from a GoogleVision response file."""
    payload = json.loads(googlevision_json_path.read_text())
    if isinstance(payload, list):
        payload = payload[0] if payload else {}
    responses = payload.get("responses") or []
    if not responses:
        return ""
    return (responses[0].get("fullTextAnnotation") or {}).get("text", "") or ""
