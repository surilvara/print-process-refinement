"""Normalised OCR output schema shared across all runners and the baseline.

Every runner must emit a JSON file matching `OcrOutput`. The comparator only
ever reads this shape, so it doesn't need to know which model produced it.

Bounding boxes are normalised to [0, 1] relative to the source image so
comparisons are resolution-independent.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class BBox:
    """Axis-aligned bbox, normalised to [0, 1]."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @staticmethod
    def from_vertices(vertices: list[dict], img_w: int, img_h: int) -> "BBox":
        """Build a BBox from a Google Vision `boundingBox.vertices` list."""
        xs = [v.get("x", 0) for v in vertices]
        ys = [v.get("y", 0) for v in vertices]
        if not xs or not ys or img_w <= 0 or img_h <= 0:
            return BBox(0.0, 0.0, 0.0, 0.0)
        return BBox(
            x_min=max(0.0, min(xs) / img_w),
            y_min=max(0.0, min(ys) / img_h),
            x_max=min(1.0, max(xs) / img_w),
            y_max=min(1.0, max(ys) / img_h),
        )


@dataclass
class OcrBlock:
    """One paragraph-level text region.

    `block_type` is optional — set it when the source model exposes layout
    labels (e.g. headline, body, caption). Unknown → "unknown".
    """

    text: str
    bbox: BBox
    confidence: float = 0.0
    block_type: str = "unknown"


@dataclass
class ImageRegion:
    """A non-text image region detected by the OCR / layout model.

    Downstream stages (OWLv2 zero-shot detection) crop these from the source
    image at runtime, so we only persist the bbox. `region_type` is optional
    (e.g. "figure", "photo", "chart").
    """

    bbox: BBox
    region_type: str = "image"
    confidence: float = 0.0


@dataclass
class OcrOutput:
    """One image's OCR result, regardless of source model.

    `image_regions` and `source_image_path` are optional. Runners that don't
    detect non-text regions leave `image_regions` empty. `source_image_path`
    lets downstream stages re-open the original image (e.g. to crop image
    regions for zero-shot detection).
    """

    image_stem: str
    image_width: int
    image_height: int
    runner: str  # "google_vision", "paddleocr_vl", "glm_ocr", ...
    full_text: str
    blocks: list[OcrBlock] = field(default_factory=list)
    image_regions: list[ImageRegion] = field(default_factory=list)
    source_image_path: str | None = None

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)

    @staticmethod
    def load(path: Path) -> "OcrOutput":
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        blocks = [
            OcrBlock(
                text=b["text"],
                bbox=BBox(**b["bbox"]),
                confidence=b.get("confidence", 0.0),
                block_type=b.get("block_type", "unknown"),
            )
            for b in raw.get("blocks", [])
        ]
        image_regions = [
            ImageRegion(
                bbox=BBox(**r["bbox"]),
                region_type=r.get("region_type", "image"),
                confidence=r.get("confidence", 0.0),
            )
            for r in raw.get("image_regions", [])
        ]
        return OcrOutput(
            image_stem=raw["image_stem"],
            image_width=raw["image_width"],
            image_height=raw["image_height"],
            runner=raw["runner"],
            full_text=raw.get("full_text", ""),
            blocks=blocks,
            image_regions=image_regions,
            source_image_path=raw.get("source_image_path"),
        )
