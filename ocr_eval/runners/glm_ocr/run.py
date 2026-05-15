"""GLM-OCR runner — calls glmocr SDK against a local mlx-vlm server.

Setup:
    See README.md. Run setup.sh once, then start_server.sh in terminal 1.

Usage (from .venv):
    python run.py --input <path> --output <path>

Emits a JSON file matching ocr_eval/schema.OcrOutput.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make harness modules importable.
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))

from runner_utils import image_size  # noqa: E402
from schema import BBox, OcrBlock, OcrOutput  # noqa: E402

RUNNER_NAME = HERE.parent.name
CONFIG_PATH = HERE.parent / "glmocr_config.yaml"

# glmocr returns bbox_2d normalised to 0-1000 (see GlmOcr._normalise_bbox).
_GLMOCR_BBOX_SCALE = 1000.0


def _bbox_from_glmocr(bbox_2d) -> BBox:
    """Convert glmocr's [x1, y1, x2, y2] (0-1000 scaled) to normalised [0, 1]."""
    if not bbox_2d or len(bbox_2d) != 4:
        return BBox(0.0, 0.0, 1.0, 1.0)
    x1, y1, x2, y2 = bbox_2d
    return BBox(
        x_min=max(0.0, min(1.0, x1 / _GLMOCR_BBOX_SCALE)),
        y_min=max(0.0, min(1.0, y1 / _GLMOCR_BBOX_SCALE)),
        x_max=max(0.0, min(1.0, x2 / _GLMOCR_BBOX_SCALE)),
        y_max=max(0.0, min(1.0, y2 / _GLMOCR_BBOX_SCALE)),
    )


def _extract_blocks(result) -> tuple[list[OcrBlock], str]:
    """Convert a glmocr PipelineResult into normalised blocks + full text.

    PipelineResult.json_result is a list of pages, each page a list of
    region dicts: {index, label, content, bbox_2d} where bbox_2d is in
    0-1000 normalised coordinates.
    """
    json_result = getattr(result, "json_result", None) or []
    blocks: list[OcrBlock] = []
    text_parts: list[str] = []

    for page in json_result:
        if not isinstance(page, list):
            continue
        for region in page:
            content = (region.get("content") or "").strip()
            if not content:
                continue
            blocks.append(
                OcrBlock(
                    text=content,
                    bbox=_bbox_from_glmocr(region.get("bbox_2d")),
                    confidence=0.0,  # glmocr doesn't surface per-region confidence
                    block_type=str(region.get("label") or "unknown"),
                )
            )
            text_parts.append(content)

    # Fall back to markdown if structured result is empty.
    if not blocks:
        md = (getattr(result, "markdown_result", "") or "").strip()
        if md:
            return [
                OcrBlock(
                    text=md,
                    bbox=BBox(0.0, 0.0, 1.0, 1.0),
                    confidence=0.0,
                    block_type="unknown",
                )
            ], md

    return blocks, "\n".join(text_parts)


def run(image_path: Path) -> OcrOutput:
    from glmocr import GlmOcr  # imported lazily so --help works without deps

    img_w, img_h = image_size(image_path)

    with GlmOcr(config_path=str(CONFIG_PATH)) as parser:
        result = parser.parse(str(image_path))

    blocks, full_text = _extract_blocks(result)

    return OcrOutput(
        image_stem=image_path.stem,
        image_width=img_w,
        image_height=img_h,
        runner=RUNNER_NAME,
        full_text=full_text,
        blocks=blocks,
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
        )

    result.save(args.output)
    print(
        f"{RUNNER_NAME}: {args.input.name} → "
        f"{len(result.blocks)} blocks, {len(result.full_text)} chars → {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
