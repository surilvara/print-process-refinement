"""Classic PaddleOCR (non-VL) runner.

Uses `paddleocr.PaddleOCR` (PP-OCRv5: text detection + text recognition,
both CNN-based). Much faster than PaddleOCR-VL but:
  - No semantic layout labels (every block is just "text").
  - One block per detected text line, not per layout region.
  - Lower quality on stylised / decorative fonts.

Runs entirely on CPU. No MLX server needed.

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
from schema import BBox, OcrBlock, OcrOutput  # noqa: E402

RUNNER_NAME = HERE.parent.name
CONFIG_PATH = HERE.parent / "paddleocr_classic_config.yaml"


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    import yaml

    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _build_engine(config: dict):
    """Instantiate PP-OCRv5 (classic, non-VL).

    Defaults match what's reasonable for clean magazine scans:
    skip orientation/unwarp/textline-orientation since pages are upright.
    """
    from paddleocr import PaddleOCR

    return PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        lang=config.get("lang", "en"),
    )


def _poly_to_bbox(poly, w: int, h: int) -> BBox:
    """Convert a 4-point polygon (pixel coords) to a normalised axis-aligned BBox."""
    xs = [float(p[0]) for p in poly]
    ys = [float(p[1]) for p in poly]
    return BBox(
        x_min=max(0.0, min(xs) / w),
        y_min=max(0.0, min(ys) / h),
        x_max=min(1.0, max(xs) / w),
        y_max=min(1.0, max(ys) / h),
    )


def _load_image(image_path: Path):
    import numpy as np
    from PIL import Image

    with Image.open(image_path) as im:
        return np.array(im.convert("RGB"))


def run(image_path: Path, engine=None) -> OcrOutput:
    if engine is None:
        engine = _build_engine(_load_config())
    image = _load_image(image_path)
    h, w = image.shape[:2]

    results = list(engine.predict(image))
    if not results:
        return _empty_result(image_path, w, h)

    raw = results[0].json
    page = raw.get("res", raw)

    # Prefer rec_polys (detections that survived recognition); fall back to dt_polys.
    polys = page.get("rec_polys") or page.get("dt_polys") or []
    texts = page.get("rec_texts") or []
    scores = page.get("rec_scores") or []

    blocks: list[OcrBlock] = []
    text_parts: list[str] = []

    for i, poly in enumerate(polys):
        text = (texts[i] if i < len(texts) else "").strip()
        if not text:
            continue
        score = float(scores[i]) if i < len(scores) else 0.0
        blocks.append(
            OcrBlock(
                text=text,
                bbox=_poly_to_bbox(poly, w, h),
                confidence=score,
                block_type="text",  # PP-OCR has no semantic layout labels
            )
        )
        text_parts.append(text)

    return OcrOutput(
        image_stem=image_path.stem,
        image_width=w,
        image_height=h,
        runner=RUNNER_NAME,
        full_text="\n".join(text_parts),
        blocks=blocks,
        source_image_path=str(image_path.resolve()),
    )


def _empty_result(image_path: Path, w: int = 0, h: int = 0) -> OcrOutput:
    return OcrOutput(
        image_stem=image_path.stem,
        image_width=w,
        image_height=h,
        runner=RUNNER_NAME,
        full_text="",
        blocks=[],
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
            f"{len(result.blocks)} blocks, {len(result.full_text)} chars → {out_path}"
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
