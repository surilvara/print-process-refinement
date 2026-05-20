"""Compare a runner's outputs against the Google Vision baseline.

Usage:
    python compare.py --runner paddleocr_vl
    python compare.py --runner glm_ocr --csv results.csv
    python compare.py --runner paddleocr_vl --gv-subdir vogue_uk_2026-04-01

Reads:
- ocr_eval/googlevision_output/[<gv-subdir>/]<stem>.json   (baseline)
- ocr_eval/outputs/<runner>/<gv-subdir>_<ts>/<stem>.json   (latest per-invocation
  run dir matching --gv-subdir; pass --run-dir to override).
  Falls back to legacy flat `ocr_eval/outputs/<runner>/<stem>.json` if no
  timestamped subdirs exist.

Writes:
- stdout summary
- optional CSV (--csv path)
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from db import insert_run, insert_run_record, new_run_id
from gvision_loader import load_gvision
from metrics import ComparisonRow, compare
from paths import (
    DEFAULT_DB_PATH,
    GV_DIR,
    OUTPUTS_DIR,
    latest_runner_run_dir,
    runner_output_dir,
)
from schema import OcrOutput


def _resolve_gv_dir(gv_subdir: str | None) -> Path:
    """Return the GV directory, optionally scoped to a publication subfolder."""
    if not gv_subdir:
        return GV_DIR
    scoped = GV_DIR / gv_subdir
    if scoped.is_dir():
        return scoped
    # Fall back to root if scoped subdir doesn't exist; warn.
    print(
        f"warning: GV subdir {scoped} not found; falling back to {GV_DIR}",
        file=sys.stderr,
    )
    return GV_DIR


def _resolve_runner_dir(
    runner: str, gv_subdir: str | None, run_dir: Path | None
) -> Path:
    """Resolve the directory containing `<runner>`'s output JSONs.

    Preference order:
      1. `run_dir` (explicit override) — used as-is.
      2. Latest per-invocation subdir matching `<gv_subdir>_<timestamp>/`.
      3. Legacy flat layout: `outputs/<runner>/` (backward compat).
    """
    if run_dir is not None:
        return run_dir
    if gv_subdir:
        latest = latest_runner_run_dir(runner, gv_subdir)
        if latest is not None:
            return latest
    return runner_output_dir(runner)


def _find_pairs(
    runner: str,
    gv_subdir: str | None = None,
    run_dir: Path | None = None,
) -> list[tuple[Path, Path]]:
    """Pair Google Vision JSONs with runner outputs by exact stem match.

    All sources (inputs/, googlevision_output/, outputs/<runner>/) are
    expected to use the same `<id>.<ext>` filename convention, so pairing
    is a straight stem equality. Files present on only one side are
    reported as warnings.
    """
    runner_dir = _resolve_runner_dir(runner, gv_subdir, run_dir)
    if not runner_dir.is_dir():
        sys.exit(f"No runner output dir: {runner_dir}")

    gv_root = _resolve_gv_dir(gv_subdir)
    gv_files = {p.stem: p for p in gv_root.rglob("*.json") if p.stem != "README"}
    runner_files = {p.stem: p for p in runner_dir.glob("*.json")}

    common = sorted(set(gv_files) & set(runner_files))
    missing_runner = sorted(set(gv_files) - set(runner_files))
    missing_gv = sorted(set(runner_files) - set(gv_files))

    if missing_runner:
        print(
            f"warning: {len(missing_runner)} image(s) have GV baseline but no "
            f"{runner} output: {missing_runner[:5]}{'...' if len(missing_runner) > 5 else ''}",
            file=sys.stderr,
        )
    if missing_gv:
        print(
            f"warning: {len(missing_gv)} {runner} output(s) have no GV baseline: "
            f"{missing_gv[:5]}{'...' if len(missing_gv) > 5 else ''}",
            file=sys.stderr,
        )
    if not common:
        sys.exit(f"No paired files found. GV dir: {gv_root}, runner dir: {runner_dir}")

    return [(gv_files[stem], runner_files[stem]) for stem in common]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare a runner against Google Vision."
    )
    parser.add_argument(
        "--runner", required=True, help="Runner name (subfolder under outputs/)"
    )
    parser.add_argument(
        "--gv-subdir",
        type=str,
        default=None,
        help="Subdirectory under googlevision_output/ to scope the baseline "
        "(e.g. vogue_uk_2026-04-01). Also used to select the latest matching "
        "`outputs/<runner>/<gv-subdir>_<timestamp>/` run dir when --run-dir is omitted.",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Explicit runner output directory. Overrides the auto-resolved "
        "`outputs/<runner>/<gv-subdir>_<timestamp>/` lookup.",
    )
    parser.add_argument("--csv", type=Path, help="Optional CSV output path")
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"SQLite path for persisted results (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--no-db", action="store_true", help="Skip writing results to SQLite"
    )
    args = parser.parse_args()

    pairs = _find_pairs(args.runner, gv_subdir=args.gv_subdir, run_dir=args.run_dir)
    rows: list[ComparisonRow] = []
    for gv_path, runner_path in pairs:
        reference = load_gvision(gv_path)
        hypothesis = OcrOutput.load(runner_path)
        rows.append(compare(reference, hypothesis))

    # Per-image table.
    widths = [
        max(len(h), max(len(r.as_row()[i]) for r in rows))
        for i, h in enumerate(ComparisonRow.header())
    ]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*ComparisonRow.header()))
    print(fmt.format(*("-" * w for w in widths)))
    for r in rows:
        print(fmt.format(*r.as_row()))

    # Summary.
    n = len(rows)
    mean_cer = sum(r.cer for r in rows) / n
    mean_wer = sum(r.wer for r in rows) / n
    mean_iou = sum(r.mean_iou for r in rows) / n
    print()
    print(f"=== Summary: {args.runner} vs google_vision ({n} images) ===")
    print(f"  mean CER          : {mean_cer:.4f}")
    print(f"  mean WER          : {mean_wer:.4f}")
    print(f"  mean best-IoU     : {mean_iou:.4f}")

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(ComparisonRow.header())
            for r in rows:
                w.writerow(r.as_row())
        print(f"\nWrote CSV: {args.csv}")

    if not args.no_db:
        run_id = new_run_id()
        insert_run_record(
            run_id=run_id,
            input_path=None,
            runners=[args.runner],
            skipped_ocr=True,
            notes="compare.py single-runner",
            db_path=args.db,
        )
        ts = insert_run(rows, db_path=args.db, run_id=run_id)
        if ts:
            print(f"\nWrote {len(rows)} row(s) to {args.db} (run_id={ts})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
