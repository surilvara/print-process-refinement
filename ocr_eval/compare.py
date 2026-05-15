"""Compare a runner's outputs against the Google Vision baseline.

Usage:
    python compare.py --runner paddleocr_vl
    python compare.py --runner glm_ocr --csv results.csv

Reads:
- ocr_eval/googlevision_outputs/<stem>.json   (baseline)
- ocr_eval/outputs/<runner>/<stem>.json       (runner output, normalised schema)

Writes:
- stdout summary
- optional CSV (--csv path)
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from db import insert_run
from gvision_loader import load_gvision
from metrics import ComparisonRow, compare
from paths import DEFAULT_DB_PATH, GV_DIR, OUTPUTS_DIR, runner_output_dir
from schema import OcrOutput


def _find_pairs(runner: str) -> list[tuple[Path, Path]]:
    """Pair Google Vision JSONs with runner outputs.

    Matching rule: the runner's filename stem must appear as a suffix of the
    GV filename stem (after a non-alphanumeric separator). This handles
    real-world GV exports that prefix the image stem with extra IDs, e.g.
    `10800084_42524659_00000041.json` ↔ `00000041.json`.
    """
    runner_dir = runner_output_dir(runner)
    if not runner_dir.is_dir():
        sys.exit(f"No runner output dir: {runner_dir}")

    gv_files = {p.stem: p for p in GV_DIR.rglob("*.json") if p.stem != "README"}
    runner_files = {p.stem: p for p in runner_dir.glob("*.json")}

    # Map runner_stem → gv_stem using exact or trailing-stem match.
    pairs: dict[str, str] = {}
    for runner_stem in runner_files:
        if runner_stem in gv_files:
            pairs[runner_stem] = runner_stem
            continue
        # Look for a GV file whose stem ends with the runner stem after a
        # non-alphanumeric separator (underscore, dash, dot, etc.).
        candidates = [
            gv_stem
            for gv_stem in gv_files
            if gv_stem.endswith(runner_stem)
            and len(gv_stem) > len(runner_stem)
            and not gv_stem[-len(runner_stem) - 1].isalnum()
        ]
        if len(candidates) == 1:
            pairs[runner_stem] = candidates[0]
        elif len(candidates) > 1:
            print(
                f"warning: {runner_stem} matches multiple GV files: {candidates}; "
                f"using {candidates[0]}",
                file=sys.stderr,
            )
            pairs[runner_stem] = candidates[0]

    common = sorted(pairs)
    paired_gv_stems = set(pairs.values())
    missing_runner = sorted(set(gv_files) - paired_gv_stems)
    missing_gv = sorted(set(runner_files) - set(pairs))

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
        sys.exit(f"No paired files found. GV dir: {GV_DIR}, runner dir: {runner_dir}")

    return [(gv_files[stem], runner_files[stem]) for stem in common]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare a runner against Google Vision."
    )
    parser.add_argument(
        "--runner", required=True, help="Runner name (subfolder under outputs/)"
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

    pairs = _find_pairs(args.runner)
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
    mean_block_delta = sum(r.block_count_delta for r in rows) / n
    print()
    print(f"=== Summary: {args.runner} vs google_vision ({n} images) ===")
    print(f"  mean CER          : {mean_cer:.4f}")
    print(f"  mean WER          : {mean_wer:.4f}")
    print(f"  mean best-IoU     : {mean_iou:.4f}")
    print(f"  mean block delta  : {mean_block_delta:+.2f}  (runner − GV)")

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(ComparisonRow.header())
            for r in rows:
                w.writerow(r.as_row())
        print(f"\nWrote CSV: {args.csv}")

    if not args.no_db:
        ts = insert_run(rows, db_path=args.db)
        if ts:
            print(f"\nWrote {len(rows)} row(s) to {args.db} (run_timestamp={ts})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
