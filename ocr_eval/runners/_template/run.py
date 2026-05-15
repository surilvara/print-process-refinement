"""Template OCR runner.

Copy this folder to a new name (e.g. `paddleocr_vl/`), update `requirements.txt`
with the model's dependencies, then fill in the TODOs below.

Contract:
- Read one image at `--input`.
- Emit one JSON file at `--output` matching `ocr_eval/schema.OcrOutput`.
- Normalise all bboxes to [0, 1].
- Set `runner` to this folder's name.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make harness modules importable from any runner subfolder.
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))

from runner_utils import image_size  # noqa: E402
from schema import BBox, OcrBlock, OcrOutput  # noqa: E402

RUNNER_NAME = HERE.parent.name  # folder name = runner name


def run(image_path: Path) -> OcrOutput:
    # TODO: load the image (PIL/cv2/numpy — whatever the model expects).
    # TODO: run the OCR model.
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
        # Emit empty result so the comparator still has something to read.
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
