"""Self-contained DMR alias matcher.

Vendored from ``open_src/src/models/ner/dmr_alias_matcher.py`` so the
``claude_classifier`` package has no cross-module Python dependencies on the
open-source pipeline. Behaviour is identical to the upstream matcher's
``_match_block`` path:

* Aho-Corasick automaton over normalised aliases.
* Specificity ordering on overlapping matches:
      BRAND > COMMERCIAL_COMPANY > COMPANY > HOLDING.
* Tie-break on identical specificity / span length: lowest ``entity_id`` wins.
* Word-boundary filtering prevents substring false positives.
* Length and stopword filters drop noise aliases at load time.

The matcher reads from the SQLite DB produced by
``scripts/import_dmr_brands.py``.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import ahocorasick
from loguru import logger

# ── Normalisation: MUST match scripts/import_dmr_brands.py.normalise() ────────

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s&]")
_WORD_CHAR_RE = re.compile(r"[\w&]")


def _normalise_char(ch: str) -> str:
    decomposed = unicodedata.normalize("NFKD", ch)
    base = "".join(c for c in decomposed if not unicodedata.combining(c))
    base = base.lower()
    if not base:
        return ""
    if _PUNCT_RE.match(base) and base != "&":
        return " "
    return base


def _normalise(text: str) -> str:
    """Lossless NFKD lowercase normaliser; collapses whitespace + punctuation."""
    if not text:
        return ""
    out_chars: list[str] = []
    prev_space = False
    for ch in text:
        norm = _normalise_char(ch)
        for nch in norm:
            if nch == " ":
                if prev_space:
                    continue
                out_chars.append(" ")
                prev_space = True
            else:
                out_chars.append(nch)
                prev_space = False
    return "".join(out_chars).strip()


def _is_word_boundary(text: str, pos: int) -> bool:
    if pos < 0 or pos >= len(text):
        return True
    return not _WORD_CHAR_RE.match(text[pos])


# ── Specificity ordering ──────────────────────────────────────────────────────

_TYPE_RANK = {
    "BRAND": 3,
    "COMMERCIAL_COMPANY": 2,
    "COMPANY": 1,
    "HOLDING": 0,
}

_DEFAULT_ALIAS_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "if",
        "is",
        "it",
        "in",
        "on",
        "at",
        "of",
        "to",
        "for",
        "by",
        "as",
        "be",
        "are",
        "was",
        "were",
        "has",
        "have",
        "had",
        "do",
        "does",
        "did",
        "not",
        "no",
        "yes",
        "so",
        "all",
        "any",
        "can",
        "will",
        "just",
        "more",
        "most",
        "some",
        "such",
        "very",
        "only",
        "also",
        "then",
        "than",
        "here",
        "there",
        "what",
        "when",
        "where",
        "who",
        "why",
        "how",
        "which",
        "while",
        "after",
        "before",
        "about",
        "into",
        "over",
        "under",
        "between",
        "both",
        "each",
        "other",
        "same",
        "own",
        "new",
        "old",
        "our",
        "your",
        "their",
        "my",
        "his",
        "her",
        "its",
        "them",
        "us",
        "me",
        "him",
        "he",
        "she",
        "we",
        "they",
        "you",
        "i",
        "this",
        "that",
        "these",
        "those",
        "with",
        "from",
        "match",
        "classic",
        "nothing",
        "the new",
        "new arrival",
    }
)


@dataclass(frozen=True)
class CanonicalBrand:
    name: str
    entity_type: str  # BRAND | COMMERCIAL_COMPANY | COMPANY | HOLDING


@dataclass(frozen=True)
class _Match:
    entity_type: str
    entity_id: int
    norm_start: int
    norm_end: int  # exclusive


class DMRMatcher:
    """Loads canonical aliases from ``dmr.db`` and matches free text against them."""

    def __init__(
        self,
        db_path: str | Path,
        min_alias_length: int = 3,
        alias_stopwords: frozenset[str] | None = None,
    ):
        self.db_path = Path(db_path)
        self.min_alias_length = max(1, int(min_alias_length))
        self.alias_stopwords = (
            alias_stopwords if alias_stopwords is not None else _DEFAULT_ALIAS_STOPWORDS
        )
        self._automaton: ahocorasick.Automaton | None = None
        self._canonical: dict[tuple[str, int], str] = {}

    def load(self) -> None:
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"DMR database not found: {self.db_path}. "
                "Run `python scripts/import_dmr_brands.py` first."
            )
        logger.info(f"Loading DMR alias database: {self.db_path}")
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT alias_norm, entity_type, entity_id FROM aliases "
                "WHERE alias_norm != ''"
            ).fetchall()
            for entity_type, entity_id, name in conn.execute(
                "SELECT 'HOLDING', id, name FROM holdings "
                "UNION ALL SELECT 'COMPANY', id, name FROM companies "
                "UNION ALL SELECT 'COMMERCIAL_COMPANY', id, name "
                "  FROM commercial_companies "
                "UNION ALL SELECT 'BRAND', id, name FROM brands"
            ):
                self._canonical[(entity_type, entity_id)] = name
        finally:
            conn.close()

        buckets: dict[str, list[tuple[str, int]]] = {}
        skipped_short = 0
        skipped_stopword = 0
        for alias_norm, entity_type, entity_id in rows:
            if len(alias_norm) < self.min_alias_length:
                skipped_short += 1
                continue
            if alias_norm in self.alias_stopwords:
                skipped_stopword += 1
                continue
            buckets.setdefault(alias_norm, []).append((entity_type, entity_id))

        automaton = ahocorasick.Automaton()
        for alias_norm, candidates in buckets.items():
            candidates.sort(key=lambda c: (-_TYPE_RANK[c[0]], c[1]))
            chosen_type, chosen_id = candidates[0]
            automaton.add_word(alias_norm, (alias_norm, chosen_type, chosen_id))
        automaton.make_automaton()
        self._automaton = automaton
        logger.info(
            f"DMR alias matcher loaded: {len(buckets)} unique aliases, "
            f"{len(self._canonical)} canonical entities "
            f"(filtered: {skipped_short} too-short, {skipped_stopword} stopword)"
        )

    def match(self, text: str) -> list[CanonicalBrand]:
        if self._automaton is None:
            raise RuntimeError("Matcher not loaded. Call load() first.")
        norm = _normalise(text)
        if not norm:
            return []

        matches: list[_Match] = []
        for end_idx, (alias_norm, entity_type, entity_id) in self._automaton.iter(norm):
            start_idx = end_idx - len(alias_norm) + 1
            if not _is_word_boundary(norm, start_idx - 1):
                continue
            if not _is_word_boundary(norm, end_idx + 1):
                continue
            matches.append(
                _Match(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    norm_start=start_idx,
                    norm_end=end_idx + 1,
                )
            )
        if not matches:
            return []

        # Resolve overlaps: longer span > higher specificity > lower entity_id.
        matches.sort(
            key=lambda m: (
                -(m.norm_end - m.norm_start),
                -_TYPE_RANK[m.entity_type],
                m.entity_id,
            )
        )
        chosen: list[_Match] = []
        occupied: list[tuple[int, int]] = []
        for m in matches:
            if any(not (m.norm_end <= s or m.norm_start >= e) for s, e in occupied):
                continue
            chosen.append(m)
            occupied.append((m.norm_start, m.norm_end))

        seen: set[tuple[str, str]] = set()
        out: list[CanonicalBrand] = []
        for m in chosen:
            canonical = self._canonical.get((m.entity_type, m.entity_id))
            if canonical is None:
                continue
            key = (canonical, m.entity_type)
            if key in seen:
                continue
            seen.add(key)
            out.append(CanonicalBrand(name=canonical, entity_type=m.entity_type))
        return out
