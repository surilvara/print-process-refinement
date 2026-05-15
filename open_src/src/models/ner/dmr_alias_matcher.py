"""
DMR alias matcher — Aho-Corasick lookup against the normalised DMR brand
database produced by `scripts/import_dmr_brands.py`.

Behaviour (see CLAUDE.md):

  * Specificity ordering on overlapping matches:
        BRAND > COMMERCIAL_COMPANY > COMPANY > HOLDING
  * Tie-break on identical specificity: lowest numeric `entity_id` wins
    (deterministic / reproducible).
  * Word-boundary filtering prevents substring false positives
    ("Mac" inside "Macaron").
  * When wrapped around a base NER backend (e.g. spaCy), DMR spans replace
    any base entity whose character span overlaps. Non-overlapping base
    entities (PERSON, GPE, DATE, …) are preserved.

The matcher runs against a *normalised* version of each text block (same
NFKD + lowercase + punctuation collapse used at import time), but reports
character offsets in the *original* text via a parallel index map so the
JSON `entities[].start/end` stay aligned with `text_blocks[].text`.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import ahocorasick
from loguru import logger

from src.models.base import (
    ClassifiedTextBlock,
    Entity,
    NERModel,
    TextBlockWithEntities,
)

# ── Normalisation: MUST match scripts/import_dmr_brands.py.normalise() ──

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s&]")


def _normalise_char(ch: str) -> str:
    """Per-character normalisation used to build a parallel offset map.

    Splits accents (NFKD), drops combining marks, lowercases. Punctuation
    becomes a single space; runs of whitespace are NOT collapsed here —
    that's done by the caller while building the offset map so we never
    lose the mapping from output position to source position.
    """
    decomposed = unicodedata.normalize("NFKD", ch)
    base = "".join(c for c in decomposed if not unicodedata.combining(c))
    base = base.lower()
    if not base:
        return ""
    if _PUNCT_RE.match(base) and base != "&":
        return " "
    return base


def _normalise_with_map(text: str) -> tuple[str, list[int]]:
    """Return (normalised_text, offset_map).

    ``offset_map[i]`` is the index in the *original* text that produced
    ``normalised_text[i]``. Whitespace runs in the normalised stream are
    collapsed to a single space; each collapsed space still points back
    to the position of the first whitespace character in the source.
    """
    if not text:
        return "", []
    out_chars: list[str] = []
    out_map: list[int] = []
    prev_space = False
    for idx, ch in enumerate(text):
        norm = _normalise_char(ch)
        for nch in norm:
            if nch == " ":
                if prev_space:
                    continue
                out_chars.append(" ")
                out_map.append(idx)
                prev_space = True
            else:
                out_chars.append(nch)
                out_map.append(idx)
                prev_space = False
    # Strip leading/trailing whitespace consistently with normalise().
    norm_str = "".join(out_chars).strip()
    if not out_chars:
        return "", []
    # Re-derive offset map after strip.
    full = "".join(out_chars)
    lstripped = full.lstrip()
    left = len(full) - len(lstripped)
    rstripped = lstripped.rstrip()
    right_drop = len(lstripped) - len(rstripped)
    if right_drop:
        out_map = out_map[left : len(out_map) - right_drop]
    else:
        out_map = out_map[left:]
    return norm_str, out_map


def _normalise(text: str) -> str:
    n, _ = _normalise_with_map(text)
    return n


# ── Specificity ordering ──

_TYPE_RANK = {
    "BRAND": 3,
    "COMMERCIAL_COMPANY": 2,
    "COMPANY": 1,
    "HOLDING": 0,
}

# Word-boundary chars in the *normalised* alphabet: anything that's not an
# alphanumeric, underscore, or '&' (the one punctuation we keep).
_WORD_CHAR_RE = re.compile(r"[\w&]")

# Default short-word filter: DMR ships canonical brand rows whose *name* is
# a single English stopword ("A", "AND", "I", "IN", "THE NEW", "NOTHING", …).
# Matching them produces useless noise on every page, so we skip aliases whose
# normalised form is in this set. Multi-word aliases that merely *contain*
# stopwords are unaffected — only exact matches are dropped.
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
        # Common ad/editorial words that show up as DMR brand names.
        "the new",
        "new arrival",
    }
)


def _is_word_boundary(text: str, pos: int) -> bool:
    if pos < 0 or pos >= len(text):
        return True
    return not _WORD_CHAR_RE.match(text[pos])


@dataclass(frozen=True)
class _Match:
    entity_type: str
    entity_id: int
    norm_start: int
    norm_end: int  # exclusive


class DMRAliasMatcher(NERModel):
    """NER backend that labels DMR holdings/companies/brands.

    Optionally wraps a base NER backend (e.g. spaCy) whose non-overlapping
    spans are merged into the output. DMR spans always win on overlap.
    """

    def __init__(
        self,
        db_path: str | Path,
        base_ner: NERModel | None = None,
        min_alias_length: int = 3,
        alias_stopwords: frozenset[str] | None = None,
    ):
        self.db_path = Path(db_path)
        self.base_ner = base_ner
        self.min_alias_length = max(1, int(min_alias_length))
        self.alias_stopwords = (
            alias_stopwords if alias_stopwords is not None else _DEFAULT_ALIAS_STOPWORDS
        )
        self._automaton: ahocorasick.Automaton | None = None
        # entity_id -> (entity_type, canonical_name) — for `Entity.text` output
        self._canonical: dict[tuple[str, int], str] = {}

    # ── lifecycle ──

    def load(self) -> None:
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"DMR database not found: {self.db_path}. "
                f"Run `python scripts/import_dmr_brands.py` first."
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

        # Bucket aliases by normalised form so we can pre-resolve the
        # specificity tie-break once, instead of per-page. Apply quality
        # filters here so the underlying DB stays untouched.
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
            # Sort by specificity desc, then entity_id asc; first wins.
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

        if self.base_ner is not None:
            self.base_ner.load()

    # ── inference ──

    def extract_entities(
        self, text_blocks: list[ClassifiedTextBlock]
    ) -> list[TextBlockWithEntities]:
        if self._automaton is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        # Base NER pass (optional) ─ keyed by block id for merge.
        base_by_id: dict[str, list[Entity]] = {}
        if self.base_ner is not None:
            for blk in self.base_ner.extract_entities(text_blocks):
                base_by_id[blk.id] = blk.entities

        results: list[TextBlockWithEntities] = []
        total_dmr = 0
        for tb in text_blocks:
            dmr_entities = self._match_block(tb.text)
            total_dmr += len(dmr_entities)
            base_entities = base_by_id.get(tb.id, [])
            merged = _merge_spans(dmr_entities, base_entities)
            results.append(
                TextBlockWithEntities(
                    id=tb.id,
                    text=tb.text,
                    bbox=tb.bbox,
                    block_type=tb.block_type,
                    entities=merged,
                )
            )

        logger.info(
            f"DMR alias matcher found {total_dmr} entit(y/ies) across "
            f"{len(text_blocks)} text block(s)"
        )
        return results

    # ── internal ──

    def _match_block(self, text: str) -> list[Entity]:
        assert self._automaton is not None
        norm, offset_map = _normalise_with_map(text)
        if not norm:
            return []

        # First pass: collect all candidate matches with word-boundary check.
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

        # Second pass: resolve overlaps. Prefer longer span; on tie, higher
        # specificity; on tie, lowest entity_id.
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

        # Map normalised offsets back to original text offsets, then sort
        # by start position for stable output.
        chosen.sort(key=lambda m: m.norm_start)
        out: list[Entity] = []
        for m in chosen:
            try:
                orig_start = offset_map[m.norm_start]
                # norm_end is exclusive; the last covered char is at norm_end-1
                orig_end = offset_map[m.norm_end - 1] + 1
            except IndexError:  # defensive
                continue
            canonical = self._canonical.get(
                (m.entity_type, m.entity_id), text[orig_start:orig_end]
            )
            out.append(
                Entity(
                    text=canonical,
                    label=m.entity_type,
                    start=orig_start,
                    end=orig_end,
                )
            )
        return out


def _merge_spans(dmr: list[Entity], base: list[Entity]) -> list[Entity]:
    """Combine DMR + base entities. DMR wins on character-span overlap."""
    if not base:
        return list(dmr)
    if not dmr:
        return list(base)
    kept: list[Entity] = list(dmr)
    for b in base:
        if any(not (b.end <= d.start or b.start >= d.end) for d in dmr):
            continue
        kept.append(b)
    kept.sort(key=lambda e: (e.start, e.end))
    return kept
