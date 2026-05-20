"""End-to-end OCR evaluation orchestrator.

One command runs N OCR models over a folder of images and compares each
against the Google Vision baseline. All results — comparisons AND any
OCR failures — are persisted under a single `run_id`.

Usage:
    # Run all discovered runners on a publication folder + compare
    uv run python evaluate.py --input ../inputs/vogue_uk_2026-04-01/ --all

    # Pick specific runners (repeatable)
    uv run python evaluate.py -i ../inputs/vogue_uk_2026-04-01/ \\
        --runner paddleocr_vl --runner glm_ocr

    # Skip OCR — just (re)compare whatever is already in outputs/<runner>/
    uv run python evaluate.py --skip-ocr --all

    # Skip DB write
    uv run python evaluate.py -i ../inputs/foo/ --all --no-db

Each runner is invoked once (`runners/<name>/.venv/bin/python run.py
--input <folder> --output-dir <outputs/<name>>`) so the model loads once
and is reused across every image in the folder.

A runner-wide failure (e.g. missing .venv) is recorded and the orchestrator
continues with the remaining runners.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from compare import _find_pairs
from db import (
    DEFAULT_DB_PATH,
    insert_failures,
    insert_ocr_run,
    insert_run,
    insert_run_record,
    new_run_id,
)
from gvision_loader import load_gvision
from metrics import ComparisonRow, compare
from paths import (
    RUNNERS_DIR,
    latest_runner_run_dir,
    make_run_timestamp,
    runner_run_dir,
)
from runner_utils import IMAGE_EXTS
from schema import OcrOutput

# Runner folders that are not actual runners.
_RUNNER_BLOCKLIST = {"_template"}

# Per-image progress line emitted by runner stdout. Matches lines like:
#   "paddleocr_vl: 42524619.jpg → 12 blocks, 3 image regions, 1234 chars → ..."
#   "glm_ocr: 42524619.jpg → 12 blocks, 1234 chars → ..."
_PROGRESS_LINE_RE = re.compile(
    r"^[\w_]+:\s+(?P<image>\S+\.(?:jpg|jpeg|png|tif|tiff|bmp|webp))\s+→",
    re.IGNORECASE,
)

# Per-image *start* line, emitted before the runner begins each image:
#   "paddleocr_vl: ▶ 42524619.jpg"
_PROGRESS_START_RE = re.compile(
    r"^[\w_]+:\s+▶\s+(?P<image>\S+\.(?:jpg|jpeg|png|tif|tiff|bmp|webp))\s*$",
    re.IGNORECASE,
)

# Callback signatures.
#   on_image_start(runner, image_name)
#   on_image(runner, image_name, completed_count)  -- fires on completion
ProgressStartCallback = Callable[[str, str], None]
ProgressCallback = Callable[[str, str, int], None]


def _discover_runners() -> list[str]:
    """Return sorted list of runner names that have a `run.py`."""
    if not RUNNERS_DIR.is_dir():
        return []
    return sorted(
        p.name
        for p in RUNNERS_DIR.iterdir()
        if p.is_dir() and p.name not in _RUNNER_BLOCKLIST and (p / "run.py").is_file()
    )


def _runner_python(runner: str) -> Path | None:
    """Locate `runners/<runner>/.venv/bin/python`. Returns None if missing."""
    candidate = RUNNERS_DIR / runner / ".venv" / "bin" / "python"
    return candidate if candidate.is_file() else None


def _count_images(folder: Path) -> int:
    return sum(
        1 for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )


def _run_ocr_for_runner(
    runner: str,
    input_path: Path,
    out_dir: Path,
    on_image: ProgressCallback | None = None,
    on_image_start: ProgressStartCallback | None = None,
) -> tuple[int, str]:
    """Invoke a runner's `run.py` against a folder of images.

    Streams the subprocess's combined stdout+stderr line by line so the
    caller can drive a progress UI via `on_image(runner, image_name, count)`.
    All output is forwarded to this process's stderr to preserve CLI
    behaviour. Returns (exit_code, captured_output). Exit code 0 = full
    success, 2 = some images failed but the runner kept going, anything
    else = fatal.
    """
    py = _runner_python(runner)
    if py is None:
        return 127, (
            f"missing venv: {RUNNERS_DIR / runner / '.venv'}. "
            f"Run `cd {RUNNERS_DIR / runner} && ./setup.sh` first."
        )

    run_py = RUNNERS_DIR / runner / "run.py"
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(py),
        str(run_py),
        "--input",
        str(input_path),
        "--output-dir",
        str(out_dir),
    ]
    print(f"\n→ [{runner}] {' '.join(cmd)}", file=sys.stderr)

    captured: list[str] = []
    completed = 0
    # Force unbuffered stdout in the child so per-image progress lines
    # reach us immediately rather than sitting in a pipe buffer until the
    # process exits.
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # line-buffered
        env=env,
    )
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stderr.write(line)
            captured.append(line)
            # Start lines arrive before any → separator, so check them first.
            if on_image_start is not None:
                ms = _PROGRESS_START_RE.match(line)
                if ms:
                    try:
                        on_image_start(runner, ms.group("image"))
                    except Exception as exc:  # noqa: BLE001 - best-effort
                        print(
                            f"warning: progress-start callback raised: {exc}",
                            file=sys.stderr,
                        )
                    continue
            if on_image is not None:
                m = _PROGRESS_LINE_RE.match(line)
                if m:
                    completed += 1
                    try:
                        on_image(runner, m.group("image"), completed)
                    except Exception as exc:  # noqa: BLE001 - callback is best-effort
                        print(
                            f"warning: progress callback raised: {exc}",
                            file=sys.stderr,
                        )
    finally:
        proc.wait()
    return proc.returncode, "".join(captured)


def _compare_runner(
    runner: str,
    gv_subdir: str | None = None,
    run_dir: Path | None = None,
) -> tuple[list[ComparisonRow], list[tuple[str, str | None, str, str]]]:
    """Pair runner outputs with GV baselines and compute metrics.

    Returns (rows, failures). Failures here are *comparison* failures
    (e.g. JSON decode errors), not OCR failures.
    """
    failures: list[tuple[str, str | None, str, str]] = []
    rows: list[ComparisonRow] = []
    try:
        pairs = _find_pairs(runner, gv_subdir=gv_subdir, run_dir=run_dir)
    except SystemExit as exc:
        failures.append((runner, None, "compare", str(exc)))
        return rows, failures

    for gv_path, runner_path in pairs:
        try:
            reference = load_gvision(gv_path)
            hypothesis = OcrOutput.load(runner_path)
            rows.append(compare(reference, hypothesis))
        except Exception as exc:  # noqa: BLE001
            failures.append(
                (runner, runner_path.stem, "compare", f"{type(exc).__name__}: {exc}")
            )
    return rows, failures


def _print_summary(runner: str, rows: list[ComparisonRow]) -> None:
    if not rows:
        print(f"  [{runner}] no paired images — nothing to summarise")
        return
    n = len(rows)
    mean_cer = sum(r.cer for r in rows) / n
    mean_wer = sum(r.wer for r in rows) / n
    mean_iou = sum(r.mean_iou for r in rows) / n
    print(
        f"  [{runner}] n={n}  CER={mean_cer:.4f}  WER={mean_wer:.4f}  "
        f"IoU={mean_iou:.4f}"
    )


# Plain dataclass-like dicts kept lightweight on purpose — the Gradio app
# only needs to read these to populate UI components.
class OcrRunRecord:
    """Per-runner wall-clock + exit metadata for a single evaluation."""

    __slots__ = (
        "runner",
        "started_at",
        "ended_at",
        "duration_seconds",
        "image_count",
        "exit_code",
        "output_dir",
    )

    def __init__(
        self,
        runner: str,
        started_at: str,
        ended_at: str,
        duration_seconds: float,
        image_count: int,
        exit_code: int,
        output_dir: Path | None,
    ) -> None:
        self.runner = runner
        self.started_at = started_at
        self.ended_at = ended_at
        self.duration_seconds = duration_seconds
        self.image_count = image_count
        self.exit_code = exit_code
        self.output_dir = output_dir


class EvaluationResult:
    """Aggregate result of a `run_evaluation` call."""

    __slots__ = (
        "run_id",
        "runners",
        "gv_subdir",
        "input_name",
        "comparison_rows",
        "ocr_runs",
        "failures",
        "runner_out_dirs",
    )

    def __init__(
        self,
        run_id: str,
        runners: list[str],
        gv_subdir: str | None,
        input_name: str | None,
        comparison_rows: list[ComparisonRow],
        ocr_runs: list[OcrRunRecord],
        failures: list[tuple[str, str | None, str, str]],
        runner_out_dirs: dict[str, Path | None],
    ) -> None:
        self.run_id = run_id
        self.runners = runners
        self.gv_subdir = gv_subdir
        self.input_name = input_name
        self.comparison_rows = comparison_rows
        self.ocr_runs = ocr_runs
        self.failures = failures
        self.runner_out_dirs = runner_out_dirs


def run_evaluation(
    *,
    input_path: Path | None,
    runners: list[str],
    skip_ocr: bool = False,
    gv_subdir: str | None = None,
    db_path: Path | None = DEFAULT_DB_PATH,
    notes: str | None = None,
    on_image: ProgressCallback | None = None,
    on_image_start: ProgressStartCallback | None = None,
    on_runner_start: Callable[[str, int], None] | None = None,
    on_runner_complete: Callable[[str, "OcrRunRecord"], None] | None = None,
) -> EvaluationResult:
    """Run OCR + comparison for the given runners. Persists to SQLite unless
    `db_path` is None.

    Parameters
    ----------
    input_path
        Folder (or single image) to OCR. Required unless `skip_ocr=True`.
    runners
        Pre-validated list of runner names (caller must have checked against
        `_discover_runners()`).
    skip_ocr
        If True, skip the OCR stage and just re-compare existing outputs.
    gv_subdir
        Subdir under googlevision_output/ to scope baselines. Auto-derived
        from `input_path.name` when None and input is a directory.
    db_path
        SQLite path, or None to skip all DB writes.
    notes
        Free-text note attached to the `runs` row.
    on_image
        Called as `on_image(runner, image_name, completed_count)` for each
        image that finishes inside a runner subprocess.
    on_image_start
        Called as `on_image_start(runner, image_name)` when a runner
        begins processing an image (before the model call).
    on_runner_start
        Called as `on_runner_start(runner, image_count)` before each
        runner's subprocess is spawned.
    on_runner_complete
        Called as `on_runner_complete(runner, ocr_run_record)` after a
        runner finishes (success or failure).
    """
    run_id = new_run_id()

    # Auto-derive gv_subdir from input folder basename when not provided.
    if gv_subdir is None and input_path is not None and input_path.is_dir():
        gv_subdir = input_path.resolve().name

    input_name: str | None = None
    if input_path is not None:
        input_name = (
            gv_subdir
            if gv_subdir
            else (input_path.stem if input_path.is_file() else input_path.name)
        )

    image_count = _count_images(input_path) if input_path and input_path.is_dir() else 0

    print(f"=== OCR evaluation run_id={run_id} ===")
    print(f"  runners   : {runners}")
    print(f"  input     : {input_path if not skip_ocr else '(skipped)'}")
    print(f"  gv-subdir : {gv_subdir or '(root)'}")
    if image_count:
        print(f"  images    : {image_count}")

    failures: list[tuple[str, str | None, str, str]] = []
    ocr_run_records: list[OcrRunRecord] = []
    runner_out_dirs: dict[str, Path | None] = {}

    # --- Stage 1: OCR per runner (sequential) ---------------------------
    if not skip_ocr:
        ts = make_run_timestamp()
        loop_input_name = input_name or "unknown"
        for runner in runners:
            if on_runner_start is not None:
                try:
                    on_runner_start(runner, image_count)
                except Exception as exc:  # noqa: BLE001
                    print(f"warning: on_runner_start raised: {exc}", file=sys.stderr)
            t0 = time.monotonic()
            started_at = datetime.now(timezone.utc).isoformat()
            out_dir = runner_run_dir(runner, loop_input_name, ts)
            runner_out_dirs[runner] = out_dir
            rc, captured = _run_ocr_for_runner(
                runner,
                input_path,
                out_dir,
                on_image=on_image,
                on_image_start=on_image_start,
            )
            dt = time.monotonic() - t0
            ended_at = datetime.now(timezone.utc).isoformat()
            print(f"  [{runner}] OCR finished in {dt:.1f}s (exit {rc}) → {out_dir}")
            record = OcrRunRecord(
                runner=runner,
                started_at=started_at,
                ended_at=ended_at,
                duration_seconds=dt,
                image_count=image_count,
                exit_code=rc,
                output_dir=out_dir,
            )
            ocr_run_records.append(record)
            if rc not in (0, 2):
                # Runner-wide failure (missing venv, model load crash, etc.).
                msg = (
                    captured.strip().splitlines()[-1]
                    if captured.strip()
                    else f"exit code {rc}"
                )
                failures.append((runner, None, "ocr", msg[:500]))
            if on_runner_complete is not None:
                try:
                    on_runner_complete(runner, record)
                except Exception as exc:  # noqa: BLE001
                    print(
                        f"warning: on_runner_complete raised: {exc}",
                        file=sys.stderr,
                    )
    else:
        # Skipping OCR: use the latest matching run dir per runner so the
        # comparison stage uses it (falls back to legacy layout in compare).
        for runner in runners:
            runner_out_dirs[runner] = (
                latest_runner_run_dir(runner, gv_subdir) if gv_subdir else None
            )

    # --- Stage 2: compare each runner against GV ------------------------
    print("\n=== Comparison ===")
    all_rows: list[ComparisonRow] = []
    for runner in runners:
        rows, cmp_failures = _compare_runner(
            runner, gv_subdir=gv_subdir, run_dir=runner_out_dirs.get(runner)
        )
        all_rows.extend(rows)
        failures.extend(cmp_failures)
        _print_summary(runner, rows)

    # --- Stage 3: persist -----------------------------------------------
    if db_path is not None:
        insert_run_record(
            run_id=run_id,
            input_path=str(input_path.resolve()) if input_path else None,
            runners=runners,
            skipped_ocr=skip_ocr,
            notes=notes,
            db_path=db_path,
        )
        for record in ocr_run_records:
            insert_ocr_run(
                run_id=run_id,
                runner=record.runner,
                started_at=record.started_at,
                ended_at=record.ended_at,
                duration_seconds=record.duration_seconds,
                image_count=record.image_count,
                exit_code=record.exit_code,
                output_dir=str(record.output_dir) if record.output_dir else None,
                db_path=db_path,
            )
        if all_rows:
            insert_run(all_rows, db_path=db_path, run_id=run_id)
            print(
                f"\nWrote {len(all_rows)} comparison row(s) to {db_path} "
                f"(run_id={run_id})"
            )
        if failures:
            insert_failures(run_id, failures, db_path=db_path)
            print(f"Wrote {len(failures)} failure row(s) to {db_path}")

    return EvaluationResult(
        run_id=run_id,
        runners=runners,
        gv_subdir=gv_subdir,
        input_name=input_name,
        comparison_rows=all_rows,
        ocr_runs=ocr_run_records,
        failures=failures,
        runner_out_dirs=runner_out_dirs,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        help="Folder of images (or a single image). Required unless --skip-ocr.",
    )
    parser.add_argument(
        "--runner",
        action="append",
        default=[],
        help="Runner name (repeatable). Use --all to select every discovered runner.",
    )
    parser.add_argument(
        "--all",
        dest="all_runners",
        action="store_true",
        help="Run every runner discovered under runners/ (excluding _template).",
    )
    parser.add_argument(
        "--skip-ocr",
        action="store_true",
        help="Skip the OCR stage; just re-compare existing outputs/<runner>/ JSONs.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"SQLite path (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Skip writing results to SQLite",
    )
    parser.add_argument(
        "--notes",
        type=str,
        default=None,
        help="Optional free-text note attached to the run record",
    )
    parser.add_argument(
        "--gv-subdir",
        type=str,
        default=None,
        help="Subdirectory under googlevision_output/ to scope the baseline "
        "(e.g. vogue_uk_2026-04-01). If omitted, defaults to the "
        "basename of --input.",
    )
    args = parser.parse_args()

    # Resolve runner list.
    discovered = _discover_runners()
    if args.all_runners:
        runners = discovered
    else:
        runners = args.runner

    if not runners:
        print(
            "No runners selected. Use --runner <name> (repeatable) or --all.\n"
            f"Discovered: {discovered}",
            file=sys.stderr,
        )
        return 2

    unknown = [r for r in runners if r not in discovered]
    if unknown:
        print(
            f"Unknown runner(s): {unknown}. Discovered: {discovered}",
            file=sys.stderr,
        )
        return 2

    if not args.skip_ocr:
        if args.input is None:
            print("--input is required unless --skip-ocr is set.", file=sys.stderr)
            return 2
        if not args.input.exists():
            print(f"Input not found: {args.input}", file=sys.stderr)
            return 1

    result = run_evaluation(
        input_path=args.input,
        runners=runners,
        skip_ocr=args.skip_ocr,
        gv_subdir=args.gv_subdir,
        db_path=None if args.no_db else args.db,
        notes=args.notes,
    )

    if result.failures:
        print("\n=== Failures ===", file=sys.stderr)
        for runner, stem, stage, msg in result.failures:
            scope = f"{runner}/{stem}" if stem else runner
            print(f"  [{stage}] {scope}: {msg}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
