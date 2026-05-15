"""Canonical directory locations for the OCR evaluation harness.

One module, one source of truth. Move folders by editing here.

Layout assumed:

    <workspace>/
    └── ocr_eval/                ← HARNESS_ROOT
        ├── paths.py             ← this file
        ├── googlevision_outputs/  ← GV_DIR
        ├── outputs/<runner>/    ← OUTPUTS_DIR / runner
        └── runners/<runner>/    ← RUNNERS_DIR / runner

    <workspace>/inputs/          ← INPUTS_DIR  (source scans)
"""

from __future__ import annotations

from pathlib import Path

HARNESS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = HARNESS_ROOT.parent

GV_DIR = HARNESS_ROOT / "googlevision_outputs"
OUTPUTS_DIR = HARNESS_ROOT / "outputs"
RUNNERS_DIR = HARNESS_ROOT / "runners"
INPUTS_DIR = PROJECT_ROOT / "inputs"

DEFAULT_DB_PATH = HARNESS_ROOT / "results.db"


def runner_output_dir(runner: str) -> Path:
    """Directory where `<runner>` writes its normalised JSON files."""
    return OUTPUTS_DIR / runner


def runner_dir(runner: str) -> Path:
    """Directory containing `<runner>`'s run.py and its venv."""
    return RUNNERS_DIR / runner
