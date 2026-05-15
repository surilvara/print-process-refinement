"""Small helpers shared by every runner.

Runners live two levels below the harness root (`ocr_eval/runners/<name>/`)
so they need to fix up `sys.path` to import the harness's top-level
modules (schema, paths). Centralise that here.
"""

from __future__ import annotations

import sys
from pathlib import Path


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
