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

from runner_utils import (
    image_size,
    iter_image_inputs,
    resolve_output_path,
)  # noqa: E402
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
    """Instantiate PaddleOCRVL with config values.

    Tuned for clean magazine/newspaper scans where we only want text +
    layout (no charts, seals, formulas, doc-unwarping). The dominant
    speed lever for this workload is using a quantized model on the
    mlx-vlm server side; the library's default per-page VLM concurrency
    (200) is already effectively unlimited for our region counts.
    """
    from paddleocr import PaddleOCRVL

    kwargs: dict = {
        "device": "gpu" if config.get("use_gpu") else "cpu",
        "engine": config.get("engine", "paddle"),
        # Skip preprocessing/recognition we don't need for clean scans.
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
        "use_chart_recognition": False,
        "use_seal_recognition": False,
    }
    for key in ("vl_rec_backend", "vl_rec_server_url", "vl_rec_api_model_name"):
        if config.get(key):
            kwargs[key] = config[key]
    return PaddleOCRVL(**kwargs)


# Layout-detection labels we want the VLM to OCR. Anything not listed here
# is still detected (so figure bboxes survive) but is not sent to the VLM
# for text recognition — we don't want equations, tables, charts, etc.
_PROMPT_LABELS = [
    "text",
    "doc_title",
    "title",
    "paragraph_title",
    "header",
    "footer",
    "figure_caption",
    "table_caption",
    "abstract",
    "aside_text",
    "reference",
    "footnote",
]


def _load_image(image_path: Path):
    """Return image as a numpy array (BGR, like cv2 — what PaddleOCR expects)."""
    import numpy as np
    from PIL import Image

    with Image.open(image_path) as im:
        rgb = np.array(im.convert("RGB"))
    # PaddleOCR's pipeline accepts RGB arrays directly; no BGR conversion needed.
    return rgb


def run(image_path: Path, engine=None) -> OcrOutput:
    """Run PaddleOCR-VL on a single image.

    If `engine` is provided, it's reused (batch mode — model loads once).
    Otherwise a fresh engine is constructed from local config.
    """
    if engine is None:
        engine = _build_engine(_load_config())
    image = _load_image(image_path)
    h, w = image.shape[:2]

    results = list(
        engine.predict(
            image,
            prompt_label=_PROMPT_LABELS,
            temperature=0.0,
            top_p=1.0,
            repetition_penalty=1.05,
            max_new_tokens=1024,
        )
    )
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

    # Build (label, bbox) -> score lookup from layout_det_res so we can
    # attach the real layout-detection confidence to each parsing block.
    # parsing_res_list itself has no score field; the score lives upstream
    # in the layout detector's output.
    layout_score_lookup: dict[tuple[str, tuple[int, int, int, int]], float] = {}
    for box in layout_boxes:
        label = (box.get("label") or "").lower()
        coord = box.get("coordinate")
        score = box.get("score")
        if not label or coord is None or score is None:
            continue
        try:
            key = (label, tuple(int(round(c)) for c in coord))
        except (TypeError, ValueError):
            continue
        # If duplicate keys appear, keep the highest score (defensive).
        prev = layout_score_lookup.get(key)
        if prev is None or float(score) > prev:
            layout_score_lookup[key] = float(score)

    def _lookup_score(label: str, bbox: list) -> float:
        try:
            key = (label.lower(), tuple(int(round(c)) for c in bbox))
        except (TypeError, ValueError):
            return 0.0
        return layout_score_lookup.get(key, 0.0)

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
        bbox_raw = block.get("block_bbox", [0, 0, w, h])
        x1, y1, x2, y2 = bbox_raw
        norm_bbox = _norm(x1, y1, x2, y2)
        mapped = _LAYOUT_TYPE_MAP.get(label, "other")
        score = _lookup_score(label, bbox_raw)

        if mapped is None:
            # Image region — keep the bbox.
            key = (norm_bbox.x_min, norm_bbox.y_min, norm_bbox.x_max, norm_bbox.y_max)
            if key not in seen_image_bboxes:
                seen_image_bboxes.add(key)
                image_regions.append(
                    ImageRegion(bbox=norm_bbox, region_type=label, confidence=score)
                )
            continue

        if not content:
            continue

        blocks.append(
            OcrBlock(
                text=content,
                bbox=norm_bbox,
                confidence=score,
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
            score = float(box.get("score") or 0.0)
            key = (norm_bbox.x_min, norm_bbox.y_min, norm_bbox.x_max, norm_bbox.y_max)
            if key not in seen_image_bboxes:
                seen_image_bboxes.add(key)
                image_regions.append(
                    ImageRegion(bbox=norm_bbox, region_type=label, confidence=score)
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


def _empty_result(image_path: Path) -> OcrOutput:
    w, h = image_size(image_path)
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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--input",
        required=True,
        type=Path,
        dest="input",
        help="Image file or directory of images",
    )
    p.add_argument("--output", type=Path, help="Output JSON file (single-image mode)")
    p.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory (required in folder mode; one JSON per image)",
    )
    args = p.parse_args()

    if not args.input.exists():
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 1

    images = iter_image_inputs(args.input)
    if not images:
        print(f"No images found at: {args.input}", file=sys.stderr)
        return 1

    is_batch = args.input.is_dir()
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    # Build the engine once for the whole batch.
    try:
        engine = _build_engine(_load_config())
    except Exception as exc:  # noqa: BLE001
        print(
            f"{RUNNER_NAME} runner-wide failure (engine build): {exc}", file=sys.stderr
        )
        return 1

    failures: list[tuple[str, str]] = []
    exit_code = 0

    for image_path in images:
        out_path = resolve_output_path(
            image_path, args.output, args.output_dir, is_batch
        )
        print(f"{RUNNER_NAME}: ▶ {image_path.name}", flush=True)
        try:
            result = run(image_path, engine=engine)
        except Exception as exc:  # noqa: BLE001 - keep batch alive
            print(
                f"{RUNNER_NAME} failed on {image_path.name}: {exc}",
                file=sys.stderr,
            )
            failures.append((image_path.stem, str(exc)))
            result = _empty_result(image_path)
            exit_code = 2
        result.save(out_path)
        print(
            f"{RUNNER_NAME}: {image_path.name} → "
            f"{len(result.blocks)} blocks, {len(result.image_regions)} image regions, "
            f"{len(result.full_text)} chars → {out_path}"
        )

    if failures:
        print(
            f"\n{RUNNER_NAME}: {len(failures)} image(s) failed: "
            f"{[s for s, _ in failures]}",
            file=sys.stderr,
        )

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
