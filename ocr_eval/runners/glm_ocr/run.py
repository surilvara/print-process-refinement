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

from runner_utils import (
    image_size,
    iter_image_inputs,
    resolve_output_path,
)  # noqa: E402
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


def run(image_path: Path, parser=None) -> OcrOutput:
    """Run GLM-OCR on a single image.

    If `parser` is provided (an already-instantiated `GlmOcr`), it's reused —
    important for batch mode where the model should load once. Otherwise a
    fresh instance is created and closed for this single image.
    """
    from glmocr import GlmOcr  # imported lazily so --help works without deps

    img_w, img_h = image_size(image_path)

    if parser is None:
        with GlmOcr(config_path=str(CONFIG_PATH)) as p:
            result = p.parse(str(image_path))
    else:
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


def _empty_result(image_path: Path) -> OcrOutput:
    return OcrOutput(
        image_stem=image_path.stem,
        image_width=0,
        image_height=0,
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

    # Load the GLM-OCR model once for the whole batch.
    from glmocr import GlmOcr  # noqa: E402

    failures: list[tuple[str, str]] = []  # (image_stem, error)
    exit_code = 0

    try:
        with GlmOcr(config_path=str(CONFIG_PATH)) as parser:
            for image_path in images:
                out_path = resolve_output_path(
                    image_path, args.output, args.output_dir, is_batch
                )
                print(f"{RUNNER_NAME}: ▶ {image_path.name}", flush=True)
                try:
                    result = run(image_path, parser=parser)
                except Exception as exc:  # noqa: BLE001 - keep batch alive
                    print(
                        f"{RUNNER_NAME} failed on {image_path.name}: {exc}",
                        file=sys.stderr,
                    )
                    failures.append((image_path.stem, str(exc)))
                    result = _empty_result(image_path)
                    exit_code = 2  # signal partial failure to orchestrator
                result.save(out_path)
                print(
                    f"{RUNNER_NAME}: {image_path.name} → "
                    f"{len(result.blocks)} blocks, {len(result.full_text)} chars → {out_path}"
                )
    except Exception as exc:  # noqa: BLE001 - model load / runner-wide failure
        print(f"{RUNNER_NAME} runner-wide failure: {exc}", file=sys.stderr)
        return 1

    if failures:
        print(
            f"\n{RUNNER_NAME}: {len(failures)} image(s) failed: "
            f"{[s for s, _ in failures]}",
            file=sys.stderr,
        )

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
