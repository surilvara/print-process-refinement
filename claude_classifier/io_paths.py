"""Path conventions and run-id helpers.

Layout (per Q9 / Q18):

    claude_classifier/output/<run_id>/
      pass1/<image_id>.json
      pass2_runs/<timestamp>/
        results/<image_id>.json
      current_pass2 -> pass2_runs/<latest>
      run_metadata.json   # includes parsed publication context
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from claude_classifier.config import OUTPUT_DIR


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_run_id(publication_folder: str, when: str | None = None) -> str:
    """`vogue_uk_2026-04-01_v2_20260520T140000`"""
    ts = when or utc_timestamp()
    return f"{publication_folder}_{ts}"


def run_dir(run_id: str) -> Path:
    return OUTPUT_DIR / run_id


def pass1_dir(run_id: str) -> Path:
    return run_dir(run_id) / "pass1"


def pass2_runs_dir(run_id: str) -> Path:
    return run_dir(run_id) / "pass2_runs"


def pass2_run_dir(run_id: str, pass2_run_id: str) -> Path:
    return pass2_runs_dir(run_id) / pass2_run_id / "results"


def metadata_path(run_id: str) -> Path:
    return run_dir(run_id) / "run_metadata.json"


def current_pass2_symlink(run_id: str) -> Path:
    return run_dir(run_id) / "current_pass2"


def update_current_pass2_symlink(run_id: str, pass2_run_id: str) -> None:
    link = current_pass2_symlink(run_id)
    target = Path("pass2_runs") / pass2_run_id  # relative for portability
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(target, target_is_directory=True)
