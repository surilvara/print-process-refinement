"""OCR evaluation metrics.

Two sets of metrics:
- Text-level: CER, WER against the baseline full_text.
- Layout-level: block-count delta, mean best-match bbox IoU.

CER/WER use raw Levenshtein distance via rapidfuzz to avoid pulling in
heavier eval libraries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz.distance import Levenshtein

from schema import BBox, OcrBlock, OcrOutput


def _normalise_text(text: str) -> str:
    """Lower-case, collapse whitespace. Punctuation is preserved.

    We deliberately keep punctuation because magazine layout (italics, em
    dashes, smart quotes) is often a real source of model error and worth
    surfacing in the metrics. Override here if you want a looser comparison.
    """
    return re.sub(r"\s+", " ", text.lower()).strip()


def char_error_rate(reference: str, hypothesis: str) -> float:
    ref = _normalise_text(reference)
    hyp = _normalise_text(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return Levenshtein.distance(ref, hyp) / len(ref)


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref_words = _normalise_text(reference).split()
    hyp_words = _normalise_text(hypothesis).split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    # Levenshtein over token sequences.
    return Levenshtein.distance(ref_words, hyp_words) / len(ref_words)


def bbox_iou(a: BBox, b: BBox) -> float:
    inter_x1 = max(a.x_min, b.x_min)
    inter_y1 = max(a.y_min, b.y_min)
    inter_x2 = min(a.x_max, b.x_max)
    inter_y2 = min(a.y_max, b.y_max)
    inter = max(0.0, inter_x2 - inter_x1) * max(0.0, inter_y2 - inter_y1)
    area_a = max(0.0, a.x_max - a.x_min) * max(0.0, a.y_max - a.y_min)
    area_b = max(0.0, b.x_max - b.x_min) * max(0.0, b.y_max - b.y_min)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def mean_best_match_iou(
    reference_blocks: list[OcrBlock], hypothesis_blocks: list[OcrBlock]
) -> float:
    """For each reference block, find the hypothesis block with highest IoU and
    average those scores. Asymmetric — measures how well the hypothesis covers
    the reference.
    """
    if not reference_blocks:
        return 0.0
    best_scores: list[float] = []
    for ref in reference_blocks:
        if not hypothesis_blocks:
            best_scores.append(0.0)
            continue
        best_scores.append(max(bbox_iou(ref.bbox, h.bbox) for h in hypothesis_blocks))
    return round(sum(best_scores) / len(best_scores), 4)


@dataclass
class ComparisonRow:
    image_stem: str
    runner: str
    cer: float
    wer: float
    ref_block_count: int
    hyp_block_count: int
    block_count_delta: int
    mean_iou: float
    ref_chars: int
    hyp_chars: int

    @staticmethod
    def header() -> list[str]:
        return [
            "image_stem",
            "runner",
            "cer",
            "wer",
            "ref_block_count",
            "hyp_block_count",
            "block_count_delta",
            "mean_iou",
            "ref_chars",
            "hyp_chars",
        ]

    def as_row(self) -> list[str]:
        return [
            self.image_stem,
            self.runner,
            f"{self.cer:.4f}",
            f"{self.wer:.4f}",
            str(self.ref_block_count),
            str(self.hyp_block_count),
            str(self.block_count_delta),
            f"{self.mean_iou:.4f}",
            str(self.ref_chars),
            str(self.hyp_chars),
        ]


def compare(reference: OcrOutput, hypothesis: OcrOutput) -> ComparisonRow:
    return ComparisonRow(
        image_stem=reference.image_stem,
        runner=hypothesis.runner,
        cer=round(char_error_rate(reference.full_text, hypothesis.full_text), 4),
        wer=round(word_error_rate(reference.full_text, hypothesis.full_text), 4),
        ref_block_count=len(reference.blocks),
        hyp_block_count=len(hypothesis.blocks),
        block_count_delta=len(hypothesis.blocks) - len(reference.blocks),
        mean_iou=mean_best_match_iou(reference.blocks, hypothesis.blocks),
        ref_chars=len(reference.full_text),
        hyp_chars=len(hypothesis.full_text),
    )
