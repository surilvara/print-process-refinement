"""Convert existing PaddleOCR-VL pipeline output JSON to normalised OcrOutput.

The production pipeline (`open_src/`) writes per-input JSON files containing
classified text blocks with normalised bboxes already. We don't need to re-run
the model — we just translate the schema.

Usage:
    python convert.py --pipeline-output ../../../open_src/output/<run>/<file>.json
    python convert.py --pipeline-output <run_dir>/  # all *.json in folder

Outputs land in `ocr_eval/outputs/paddleocr_vl/<stem>.json`.

The stem is taken from `metadata.input_file` in the pipeline JSON so it pairs
with the matching Google Vision baseline filename.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make harness modules importable.
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))

from paths import INPUTS_DIR, runner_output_dir  # noqa: E402
from schema import BBox, ImageRegion, OcrBlock, OcrOutput  # noqa: E402

RUNNER_NAME = HERE.parent.name
OUTPUT_ROOT = runner_output_dir(RUNNER_NAME)


def _resolve_image_path(image_name: str, search_root: Path) -> Path | None:
    """Find the source image file under `search_root` by filename."""
    matches = list(search_root.rglob(image_name))
    return matches[0] if matches else None


def _load_image_size(image_path: Path | None) -> tuple[int, int]:
    """Best-effort image dimensions. Returns (0, 0) on any failure."""
    if image_path is None:
        return 0, 0
    try:
        from PIL import Image
    except ImportError:
        return 0, 0
    try:
        with Image.open(image_path) as im:
            return im.width, im.height
    except Exception:
        return 0, 0


def convert(pipeline_json_path: Path, inputs_root: Path) -> OcrOutput:
    with open(pipeline_json_path, encoding="utf-8") as f:
        raw = json.load(f)

    metadata = raw.get("metadata", {})
    image_name = metadata.get("input_file", pipeline_json_path.stem + ".jpg")
    image_stem = Path(image_name).stem

    image_path = _resolve_image_path(image_name, inputs_root)
    img_w, img_h = _load_image_size(image_path)

    blocks: list[OcrBlock] = []
    text_parts: list[str] = []
    image_regions: list[ImageRegion] = []

    # The pipeline emits one page per input image (PDFs are flattened to
    # multiple pages, but for image inputs this is always a single page).
    for page in raw.get("pages", []):
        for tb in page.get("text_blocks", []):
            text = (tb.get("text") or "").strip()
            if not text:
                continue
            bbox_list = tb.get("bbox") or [0.0, 0.0, 0.0, 0.0]
            x_min, y_min, x_max, y_max = bbox_list
            blocks.append(
                OcrBlock(
                    text=text,
                    bbox=BBox(
                        x_min=float(x_min),
                        y_min=float(y_min),
                        x_max=float(x_max),
                        y_max=float(y_max),
                    ),
                    confidence=float(tb.get("confidence", 0.0)),
                    block_type=tb.get("type", "unknown"),
                )
            )
            text_parts.append(text)

        for ir in page.get("image_regions", []):
            bbox_list = ir.get("bbox") or [0.0, 0.0, 0.0, 0.0]
            x_min, y_min, x_max, y_max = bbox_list
            image_regions.append(
                ImageRegion(
                    bbox=BBox(
                        x_min=float(x_min),
                        y_min=float(y_min),
                        x_max=float(x_max),
                        y_max=float(y_max),
                    ),
                    region_type=ir.get("type", "image"),
                    confidence=float(ir.get("confidence", 0.0)),
                )
            )

    return OcrOutput(
        image_stem=image_stem,
        image_width=img_w,
        image_height=img_h,
        runner=RUNNER_NAME,
        full_text="\n".join(text_parts),
        blocks=blocks,
        image_regions=image_regions,
        source_image_path=str(image_path) if image_path else None,
    )


def _iter_pipeline_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(p for p in path.glob("*.json") if p.is_file())
    sys.exit(f"Not a file or directory: {path}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--pipeline-output",
        required=True,
        type=Path,
        help="Single JSON file or a folder of JSON files from open_src/output/",
    )
    p.add_argument(
        "--inputs-root",
        type=Path,
        default=INPUTS_DIR,
        help="Where to search for source images (for width/height lookup)",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_ROOT,
        help="Where to write normalised JSON files",
    )
    args = p.parse_args()

    files = _iter_pipeline_files(args.pipeline_output)
    if not files:
        sys.exit(f"No JSON files found at {args.pipeline_output}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for src in files:
        result = convert(src, args.inputs_root)
        dst = args.output_dir / f"{result.image_stem}.json"
        result.save(dst)
        print(
            f"{src.name} → {dst.name}  "
            f"({len(result.blocks)} blocks, {len(result.full_text)} chars, "
            f"{result.image_width}x{result.image_height})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
