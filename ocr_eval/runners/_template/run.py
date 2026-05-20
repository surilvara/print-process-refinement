"""Template OCR runner.

Copy this folder to a new name (e.g. `paddleocr_vl/`), update `requirements.txt`
with the model's dependencies, then fill in the TODOs below.

Contract:
- Read one image at `--input`, OR a directory of images.
- Emit one JSON file per image matching `ocr_eval/schema.OcrOutput`.
- Normalise all bboxes to [0, 1].
- Set `runner` to this folder's name.
- Load the model ONCE per process (batch mode reuses it across images).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make harness modules importable from any runner subfolder.
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))

from runner_utils import (
    image_size,
    iter_image_inputs,
    resolve_output_path,
)  # noqa: E402
from schema import BBox, OcrBlock, OcrOutput  # noqa: E402

RUNNER_NAME = HERE.parent.name  # folder name = runner name


def _build_engine():
    """TODO: instantiate the model and return whatever object the per-image
    `run()` needs. This runs ONCE per process."""
    return None


def run(image_path: Path, engine=None) -> OcrOutput:
    # TODO: load the image (PIL/cv2/numpy — whatever the model expects).
    # TODO: invoke the model via `engine`.
    # TODO: convert model output into OcrBlock instances with normalised bboxes.

    img_w, img_h = image_size(image_path)
    blocks: list[OcrBlock] = []
    full_text = ""

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

    try:
        engine = _build_engine()
    except Exception as exc:  # noqa: BLE001
        print(f"{RUNNER_NAME} runner-wide failure: {exc}", file=sys.stderr)
        return 1

    failures: list[tuple[str, str]] = []
    exit_code = 0

    for image_path in images:
        out_path = resolve_output_path(
            image_path, args.output, args.output_dir, is_batch
        )
        try:
            result = run(image_path, engine=engine)
        except Exception as exc:  # noqa: BLE001
            print(f"{RUNNER_NAME} failed on {image_path.name}: {exc}", file=sys.stderr)
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
