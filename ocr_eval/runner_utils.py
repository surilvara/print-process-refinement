"""Small helpers shared by every runner.

Runners live two levels below the harness root (`ocr_eval/runners/<name>/`)
so they need to fix up `sys.path` to import the harness's top-level
modules (schema, paths). Centralise that here.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Image file extensions accepted when --input is a directory.
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}


def add_harness_to_path(runner_file: Path) -> Path:
    """Insert `ocr_eval/` onto sys.path so a runner can `from schema import ...`.

    Pass the runner's `__file__` (resolved). Returns the harness root path
    for convenience.
    """
    harness_root = Path(runner_file).resolve().parents[2]
    sys.path.insert(0, str(harness_root))
    return harness_root


def image_size(image_path: Path) -> tuple[int, int]:
    """Return (width, height) of `image_path`, or (0, 0) if PIL is missing
    or the file can't be opened. Bbox metrics are all normalised so size is
    informational only."""
    try:
        from PIL import Image
    except ImportError:
        return 0, 0
    try:
        with Image.open(image_path) as im:
            return im.width, im.height
    except Exception:
        return 0, 0


def iter_image_inputs(input_path: Path) -> list[Path]:
    """Resolve `--input` to a sorted list of image files.

    Accepts either a single image file or a directory containing images
    (non-recursive). Filters by `IMAGE_EXTS`.
    """
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        return sorted(
            p
            for p in input_path.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS
        )
    return []


def resolve_output_path(
    image_path: Path,
    output: Path | None,
    output_dir: Path | None,
    is_batch: bool,
) -> Path:
    """Decide where to write `<image>.json`.

    - Batch mode (folder input): `output_dir / <stem>.json`. `--output` ignored.
    - Single-file mode: `output` if given, else `output_dir / <stem>.json`.
    """
    if is_batch:
        if output_dir is None:
            raise SystemExit("--output-dir is required when --input is a directory")
        return output_dir / f"{image_path.stem}.json"
    if output is not None:
        return output
    if output_dir is not None:
        return output_dir / f"{image_path.stem}.json"
    raise SystemExit("Provide --output (file) or --output-dir (directory)")
