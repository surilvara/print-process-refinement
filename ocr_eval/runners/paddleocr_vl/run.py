"""Standalone PaddleOCR-VL runner.

Calls `paddleocr.PaddleOCRVL` directly (independent of `open_src/`). Layout
detection runs locally via PaddlePaddle; VLM recognition is offloaded to a
local mlx-vlm server (port 8111 by default).

Usage:
    .venv/bin/python run.py --input <path> --output <path>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))

from runner_utils import image_size  # noqa: E402
from schema import BBox, ImageRegion, OcrBlock, OcrOutput  # noqa: E402

RUNNER_NAME = HERE.parent.name
CONFIG_PATH = HERE.parent / "paddleocr_vl_config.yaml"

# Map PaddleOCR-VL block_label values to our schema. Mirrors the production
# pipeline at open_src/src/models/ocr/paddleocr_vl.py — keep these in sync if
# you change either.
_LAYOUT_TYPE_MAP = {
    "doc_title": "headline",
    "title": "headline",
    "text": "body",
    "figure_caption": "caption",
    "table_caption": "caption",
    "header": "byline",
    "footer": "other",
    "table": "body",
    "equation": "other",
    "reference": "other",
    "figure": None,  # image region
    "image": None,
    "seal": "other",
    "chart": "other",
    "header_image": None,
    "footer_image": None,
    "aside_text": "body",
    "number": "other",
    "footnote": "other",
    "abstract": "body",
    "paragraph_title": "subheadline",
}


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    import yaml

    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _build_engine(config: dict):
    """Instantiate PaddleOCRVL with config values."""
    from paddleocr import PaddleOCRVL

    kwargs: dict = {
        "device": "gpu" if config.get("use_gpu") else "cpu",
        "engine": config.get("engine", "paddle"),
    }
    for key in ("vl_rec_backend", "vl_rec_server_url", "vl_rec_api_model_name"):
        if config.get(key):
            kwargs[key] = config[key]
    return PaddleOCRVL(**kwargs)


def _load_image(image_path: Path):
    """Return image as a numpy array (BGR, like cv2 — what PaddleOCR expects)."""
    import numpy as np
    from PIL import Image

    with Image.open(image_path) as im:
        rgb = np.array(im.convert("RGB"))
    # PaddleOCR's pipeline accepts RGB arrays directly; no BGR conversion needed.
    return rgb


def run(image_path: Path) -> OcrOutput:
    config = _load_config()
    engine = _build_engine(config)
    image = _load_image(image_path)
    h, w = image.shape[:2]

    results = list(engine.predict(image))
    if not results:
        return OcrOutput(
            image_stem=image_path.stem,
            image_width=w,
            image_height=h,
            runner=RUNNER_NAME,
            full_text="",
            blocks=[],
            image_regions=[],
            source_image_path=str(image_path.resolve()),
        )

    raw = results[0].json
    page_data = raw.get("res", raw)
    parsing_blocks = page_data.get("parsing_res_list", [])
    layout_boxes = page_data.get("layout_det_res", {}).get("boxes", [])

    blocks: list[OcrBlock] = []
    text_parts: list[str] = []
    image_regions: list[ImageRegion] = []
    seen_image_bboxes: set[tuple[float, float, float, float]] = set()

    def _norm(x1, y1, x2, y2) -> BBox:
        return BBox(
            x_min=max(0.0, x1 / w),
            y_min=max(0.0, y1 / h),
            x_max=min(1.0, x2 / w),
            y_max=min(1.0, y2 / h),
        )

    for block in parsing_blocks:
        label = block.get("block_label", "text").lower()
        content = (block.get("block_content") or "").strip()
        x1, y1, x2, y2 = block.get("block_bbox", [0, 0, w, h])
        norm_bbox = _norm(x1, y1, x2, y2)
        mapped = _LAYOUT_TYPE_MAP.get(label, "other")

        if mapped is None:
            # Image region — keep the bbox.
            key = (norm_bbox.x_min, norm_bbox.y_min, norm_bbox.x_max, norm_bbox.y_max)
            if key not in seen_image_bboxes:
                seen_image_bboxes.add(key)
                image_regions.append(
                    ImageRegion(bbox=norm_bbox, region_type=label, confidence=1.0)
                )
            continue

        if not content:
            continue

        blocks.append(
            OcrBlock(
                text=content,
                bbox=norm_bbox,
                confidence=1.0,
                block_type=mapped,
            )
        )
        text_parts.append(content)

    # Layout-only detections (sometimes the parsing_res_list misses figure crops).
    for box in layout_boxes:
        label = (box.get("label") or "").lower()
        if label in _LAYOUT_TYPE_MAP and _LAYOUT_TYPE_MAP[label] is None:
            x1, y1, x2, y2 = box.get("coordinate", [0, 0, w, h])
            norm_bbox = _norm(x1, y1, x2, y2)
            key = (norm_bbox.x_min, norm_bbox.y_min, norm_bbox.x_max, norm_bbox.y_max)
            if key not in seen_image_bboxes:
                seen_image_bboxes.add(key)
                image_regions.append(
                    ImageRegion(bbox=norm_bbox, region_type=label, confidence=1.0)
                )

    return OcrOutput(
        image_stem=image_path.stem,
        image_width=w,
        image_height=h,
        runner=RUNNER_NAME,
        full_text="\n".join(text_parts),
        blocks=blocks,
        image_regions=image_regions,
        source_image_path=str(image_path.resolve()),
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, type=Path, dest="input")
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()

    if not args.input.is_file():
        print(f"Image not found: {args.input}", file=sys.stderr)
        return 1

    try:
        result = run(args.input)
    except Exception as exc:
        print(f"{RUNNER_NAME} failed on {args.input.name}: {exc}", file=sys.stderr)
        result = OcrOutput(
            image_stem=args.input.stem,
            image_width=0,
            image_height=0,
            runner=RUNNER_NAME,
            full_text="",
            blocks=[],
            image_regions=[],
            source_image_path=str(args.input.resolve()),
        )

    # image_size is informational — fill it even on failure if PIL is happy.
    if result.image_width == 0:
        w, h = image_size(args.input)
        result.image_width, result.image_height = w, h

    result.save(args.output)
    print(
        f"{RUNNER_NAME}: {args.input.name} → "
        f"{len(result.blocks)} blocks, {len(result.image_regions)} image regions, "
        f"{len(result.full_text)} chars → {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
