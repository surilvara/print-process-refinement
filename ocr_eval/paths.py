"""Canonical directory locations for the OCR evaluation harness.

One module, one source of truth. Move folders by editing here.

Layout assumed:

    <workspace>/
    └── ocr_eval/                                ← HARNESS_ROOT
        ├── paths.py                             ← this file
        ├── googlevision_output/                 ← GV_DIR
        ├── outputs/<runner>/<input>_<ts>/       ← per-invocation run dir
        └── runners/<runner>/                    ← RUNNERS_DIR / runner

    <workspace>/inputs/                          ← INPUTS_DIR  (source scans)
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

HARNESS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = HARNESS_ROOT.parent

GV_DIR = HARNESS_ROOT / "googlevision_output"
OUTPUTS_DIR = HARNESS_ROOT / "outputs"
RUNNERS_DIR = HARNESS_ROOT / "runners"
INPUTS_DIR = PROJECT_ROOT / "inputs"

DEFAULT_DB_PATH = HARNESS_ROOT / "results.db"

# `<input_name>_<YYYYMMDDTHHMMSS>` — a runner's per-invocation output dir.
_RUN_DIR_RE = re.compile(r"^(?P<name>.+)_(?P<ts>\d{8}T\d{6})$")


def runner_output_dir(runner: str) -> Path:
    """Top-level directory for `<runner>`'s outputs (contains per-run subdirs)."""
    return OUTPUTS_DIR / runner


def runner_dir(runner: str) -> Path:
    """Directory containing `<runner>`'s run.py and its venv."""
    return RUNNERS_DIR / runner


def make_run_timestamp() -> str:
    """`YYYYMMDDTHHMMSS` stamp used to name a per-invocation output dir."""
    return datetime.now().strftime("%Y%m%dT%H%M%S")


def runner_run_dir(runner: str, input_name: str, timestamp: str) -> Path:
    """Per-invocation output dir: `outputs/<runner>/<input_name>_<timestamp>/`."""
    return runner_output_dir(runner) / f"{input_name}_{timestamp}"


def latest_runner_run_dir(runner: str, input_name: str) -> Path | None:
    """Most recent existing run dir for `<runner>` + `<input_name>`, or None.

    Matches subfolders named `<input_name>_<YYYYMMDDTHHMMSS>`. Returns the
    one with the lexicographically greatest timestamp (== chronologically
    most recent, since the format is sortable).
    """
    base = runner_output_dir(runner)
    if not base.is_dir():
        return None
    prefix = f"{input_name}_"
    candidates = [
        p
        for p in base.iterdir()
        if p.is_dir() and p.name.startswith(prefix) and _RUN_DIR_RE.match(p.name)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.name)
