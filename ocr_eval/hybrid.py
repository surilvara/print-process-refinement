"""Hybrid OCR routing: run a primary OCR model, fall back to a secondary
on pages where the primary's output fails a salvage rule.

Usage:
    # Default: primary=paddleocr_vl, fallback=glm_ocr, rule=blocks==0
    uv run python hybrid.py -i ../inputs/vogue_uk_2026-04-01/

    # Customise
    uv run python hybrid.py -i ../inputs/vogue_uk_2026-04-01/ \\
        --primary paddleocr_vl --fallback glm_ocr \\
        --salvage-rule "blocks == 0 or hyp_chars < 10" \\
        --name hybrid_v1 \\
        --gv-subdir vogue_uk_2026-04-01

Caching:
    Existing outputs/<runner>/ JSONs are reused. Primary runs only on
    images that don't have a cached output; fallback runs only on the
    salvage subset. Pass --no-cache to force re-OCR for both.

Output:
    outputs/<name>/<stem>.json — standard OcrOutput JSON plus four extra
    fields recorded for audit:
        - source           : "primary" | "fallback"
        - salvage_trigger  : the rule expression that fired (or null)
        - primary_runner   : name of the primary runner
        - fallback_runner  : name of the fallback runner

    The hybrid is registered as a runner for comparison purposes (its
    `runner` field is set to <name>), so `compare.py --runner <name>`
    works out of the box. The orchestrator writes a comparison run to
    SQLite unless --no-compare is set.

Salvage rule DSL:
    A Python expression evaluated against the primary OcrOutput. Available
    variables:
        blocks            : int   — len(output.blocks)
        hyp_chars         : int   — len(output.full_text)
        mean_confidence   : float — mean of block confidences (0.0 if none)
        has_text          : bool  — hyp_chars > 0
    Truthy result → fallback fires.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

from compare import _find_pairs
from db import (
    DEFAULT_DB_PATH,
    insert_failures,
    insert_run,
    insert_run_record,
    new_run_id,
)
from gvision_loader import load_gvision
from metrics import ComparisonRow, compare
from paths import (
    OUTPUTS_DIR,
    RUNNERS_DIR,
    latest_runner_run_dir,
    make_run_timestamp,
    runner_run_dir,
)
from runner_utils import IMAGE_EXTS, iter_image_inputs
from schema import OcrOutput


def _runner_python(runner: str) -> Path | None:
    candidate = RUNNERS_DIR / runner / ".venv" / "bin" / "python"
    return candidate if candidate.is_file() else None


def _run_ocr(runner: str, input_path: Path, out_dir: Path) -> tuple[int, str]:
    """Invoke `runners/<runner>/run.py --input <folder> --output-dir <out>`."""
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
    proc = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    return proc.returncode, proc.stderr or ""


def _ocr_on_subset(
    runner: str,
    images: list[Path],
    out_dir: Path,
) -> tuple[int, str]:
    """Run a runner on a subset of images by symlinking them into a temp
    folder so the runner loads its model once and processes them as a batch.
    """
    if not images:
        return 0, ""
    with tempfile.TemporaryDirectory(prefix=f"hybrid_{runner}_") as td:
        tmp = Path(td)
        for img in images:
            (tmp / img.name).symlink_to(img.resolve())
        return _run_ocr(runner, tmp, out_dir)


def _evaluate_salvage(output: OcrOutput, rule: str) -> bool:
    """Evaluate `rule` against a primary OcrOutput. Returns True if fallback
    should fire."""
    confs = [b.confidence for b in output.blocks if b.confidence is not None]
    namespace = {
        "blocks": len(output.blocks),
        "hyp_chars": len(output.full_text or ""),
        "mean_confidence": sum(confs) / len(confs) if confs else 0.0,
        "has_text": bool(output.full_text and output.full_text.strip()),
    }
    try:
        return bool(eval(rule, {"__builtins__": {}}, namespace))  # noqa: S307
    except Exception as exc:  # noqa: BLE001
        print(
            f"  ! salvage rule eval failed on {output.image_stem}: {exc}",
            file=sys.stderr,
        )
        return False


def _write_hybrid_output(
    src_json: Path,
    dest_dir: Path,
    runner_name: str,
    source: str,
    salvage_trigger: str | None,
    primary_runner: str,
    fallback_runner: str,
) -> Path:
    """Copy `src_json` to `dest_dir/<stem>.json`, rewriting `runner` and
    appending the four audit fields."""
    with open(src_json, encoding="utf-8") as f:
        data = json.load(f)
    data["runner"] = runner_name
    data["source"] = source
    data["salvage_trigger"] = salvage_trigger
    data["primary_runner"] = primary_runner
    data["fallback_runner"] = fallback_runner
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src_json.name
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return dest


def _missing_outputs(images: list[Path], out_dir: Path) -> list[Path]:
    """Return images whose `<stem>.json` is not yet in `out_dir`."""
    return [img for img in images if not (out_dir / f"{img.stem}.json").is_file()]


def _seed_from_prior(
    new_dir: Path,
    prior_dir: Path | None,
    images: list[Path],
) -> int:
    """Pre-populate `new_dir` with `<stem>.json` files that already exist in
    `prior_dir`. Uses hardlinks where possible (falls back to copy across
    filesystem boundaries). Returns the number of seeded files.

    These outputs are immutable once written, so sharing inodes via hardlink
    is safe and avoids duplicating large batches on disk.
    """
    if prior_dir is None or not prior_dir.is_dir():
        return 0
    new_dir.mkdir(parents=True, exist_ok=True)
    seeded = 0
    for img in images:
        src = prior_dir / f"{img.stem}.json"
        if not src.is_file():
            continue
        dest = new_dir / f"{img.stem}.json"
        if dest.exists():
            continue
        try:
            os.link(src, dest)
        except OSError:
            shutil.copy2(src, dest)
        seeded += 1
    return seeded


def _compare_runner(
    runner: str,
    gv_subdir: str | None,
    run_dir: Path | None = None,
) -> tuple[list[ComparisonRow], list[tuple[str, str | None, str, str]]]:
    """Pair runner outputs with GV baselines and compute metrics."""
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


def _print_summary(label: str, rows: list[ComparisonRow]) -> None:
    if not rows:
        print(f"  [{label}] no paired images")
        return
    n = len(rows)
    print(
        f"  [{label}] n={n}  "
        f"CER={sum(r.cer for r in rows) / n:.4f}  "
        f"WER={sum(r.wer for r in rows) / n:.4f}  "
        f"IoU={sum(r.mean_iou for r in rows) / n:.4f}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        required=True,
        help="Folder of images (or a single image).",
    )
    parser.add_argument(
        "--primary",
        default="paddleocr_vl",
        help="Primary OCR runner (default: paddleocr_vl).",
    )
    parser.add_argument(
        "--fallback",
        default="glm_ocr",
        help="Fallback OCR runner (default: glm_ocr).",
    )
    parser.add_argument(
        "--salvage-rule",
        default="blocks == 0",
        help="Expression that triggers fallback. Variables: blocks, hyp_chars, "
        'mean_confidence, has_text. Default: "blocks == 0".',
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Name for the hybrid runner (default: hybrid_<primary>_<fallback>).",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Force re-OCR for both primary and fallback (ignore existing outputs).",
    )
    parser.add_argument(
        "--no-compare",
        action="store_true",
        help="Skip the GV comparison stage; just emit hybrid outputs.",
    )
    parser.add_argument(
        "--gv-subdir",
        default=None,
        help="Subdirectory of googlevision_output/ to use as baseline. "
        "Defaults to the basename of --input.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"SQLite path (default: {DEFAULT_DB_PATH}).",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Skip writing to SQLite.",
    )
    parser.add_argument(
        "--notes",
        default=None,
        help="Optional free-text note attached to the run record.",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 1

    images = iter_image_inputs(args.input)
    if not images:
        print(f"No images under {args.input}", file=sys.stderr)
        return 1

    hybrid_name = args.name or f"hybrid_{args.primary}_{args.fallback}"
    run_id = new_run_id()
    gv_subdir = args.gv_subdir or args.input.resolve().name
    ts = make_run_timestamp()
    # Use the input folder/file name as the run-dir component so the
    # timestamped subdir is named `<input>_<ts>/` per runner.
    input_name = args.input.name if args.input.is_dir() else args.input.stem

    primary_dir = runner_run_dir(args.primary, input_name, ts)
    fallback_dir = runner_run_dir(args.fallback, input_name, ts)
    hybrid_dir = OUTPUTS_DIR / hybrid_name / f"{input_name}_{ts}"

    # When caching is enabled, seed the new run dirs from the most recent
    # prior matching run dir so already-OCR'd pages are reused.
    prior_primary = (
        None if args.no_cache else latest_runner_run_dir(args.primary, input_name)
    )
    prior_fallback = (
        None if args.no_cache else latest_runner_run_dir(args.fallback, input_name)
    )

    print(f"=== Hybrid OCR run_id={run_id} ===")
    print(f"  primary       : {args.primary}")
    print(f"  fallback      : {args.fallback}")
    print(f"  salvage rule  : {args.salvage_rule!r}")
    print(f"  hybrid name   : {hybrid_name}")
    print(f"  images        : {len(images)}")
    print(f"  cache         : {'off' if args.no_cache else 'on'}")
    print(f"  gv-subdir     : {gv_subdir}")
    print(f"  primary dir   : {primary_dir}")
    print(f"  fallback dir  : {fallback_dir}")
    print(f"  hybrid dir    : {hybrid_dir}")

    failures: list[tuple[str, str | None, str, str]] = []

    # ------------------------------------------------------------------
    # Stage 1: ensure primary outputs exist for every image
    # ------------------------------------------------------------------
    if not args.no_cache:
        seeded = _seed_from_prior(primary_dir, prior_primary, images)
        if seeded:
            print(
                f"\n[primary={args.primary}] reused {seeded} cached output(s) "
                f"from {prior_primary}"
            )

    missing_primary = _missing_outputs(images, primary_dir)
    if missing_primary:
        print(
            f"\n[primary={args.primary}] running OCR on {len(missing_primary)} image(s)"
        )
        t0 = time.monotonic()
        # Run on full folder if everything is missing (cheaper than symlinking
        # the same files); otherwise symlink the missing subset.
        if len(missing_primary) == len(images) and args.input.is_dir():
            rc, err = _run_ocr(args.primary, args.input, primary_dir)
        else:
            rc, err = _ocr_on_subset(args.primary, missing_primary, primary_dir)
        print(f"  done in {time.monotonic() - t0:.1f}s (exit {rc})")
        if rc not in (0, 2):
            failures.append(
                (
                    args.primary,
                    None,
                    "ocr",
                    (err.strip().splitlines()[-1:] or [f"exit {rc}"])[0][:500],
                )
            )
            print(
                f"\nPrimary runner failed catastrophically; aborting.", file=sys.stderr
            )
            return 2
    else:
        print(f"\n[primary={args.primary}] all {len(images)} output(s) cached")

    # ------------------------------------------------------------------
    # Stage 2: load primary outputs + apply salvage rule
    # ------------------------------------------------------------------
    salvage: list[Path] = []
    primary_outputs: dict[str, Path] = {}
    for img in images:
        p = primary_dir / f"{img.stem}.json"
        if not p.is_file():
            failures.append((args.primary, img.stem, "ocr", "no output produced"))
            continue
        primary_outputs[img.stem] = p
        try:
            out = OcrOutput.load(p)
        except Exception as exc:  # noqa: BLE001
            failures.append((args.primary, img.stem, "ocr", f"load failed: {exc}"))
            continue
        if _evaluate_salvage(out, args.salvage_rule):
            salvage.append(img)

    print(f"\n[router] salvage rule fired on {len(salvage)} / {len(images)} page(s)")
    if salvage:
        preview = ", ".join(img.stem for img in salvage[:5])
        more = "" if len(salvage) <= 5 else f", … +{len(salvage) - 5} more"
        print(f"  triggered: {preview}{more}")

    # ------------------------------------------------------------------
    # Stage 3: ensure fallback outputs exist for the salvage subset
    # ------------------------------------------------------------------
    if salvage:
        if not args.no_cache:
            seeded = _seed_from_prior(fallback_dir, prior_fallback, salvage)
            if seeded:
                print(
                    f"\n[fallback={args.fallback}] reused {seeded} cached "
                    f"output(s) from {prior_fallback}"
                )
        missing_fb = _missing_outputs(salvage, fallback_dir)
        if missing_fb:
            print(
                f"\n[fallback={args.fallback}] running OCR on {len(missing_fb)} image(s)"
            )
            t0 = time.monotonic()
            rc, err = _ocr_on_subset(args.fallback, missing_fb, fallback_dir)
            print(f"  done in {time.monotonic() - t0:.1f}s (exit {rc})")
            if rc not in (0, 2):
                failures.append(
                    (
                        args.fallback,
                        None,
                        "ocr",
                        (err.strip().splitlines()[-1:] or [f"exit {rc}"])[0][:500],
                    )
                )
        else:
            print(f"\n[fallback={args.fallback}] all {len(salvage)} output(s) cached")

    # ------------------------------------------------------------------
    # Stage 4: assemble hybrid outputs
    # ------------------------------------------------------------------
    if hybrid_dir.exists():
        # Wipe stale hybrid outputs so we don't mix runs.
        shutil.rmtree(hybrid_dir)
    hybrid_dir.mkdir(parents=True)

    salvage_stems = {img.stem for img in salvage}
    written = 0
    for stem, p_json in primary_outputs.items():
        if stem in salvage_stems:
            fb_json = fallback_dir / f"{stem}.json"
            if fb_json.is_file():
                _write_hybrid_output(
                    fb_json,
                    hybrid_dir,
                    hybrid_name,
                    source="fallback",
                    salvage_trigger=args.salvage_rule,
                    primary_runner=args.primary,
                    fallback_runner=args.fallback,
                )
                written += 1
                continue
            # Fallback didn't produce output → fall back to primary anyway.
            failures.append(
                (args.fallback, stem, "ocr", "salvage selected but no fallback output")
            )
        _write_hybrid_output(
            p_json,
            hybrid_dir,
            hybrid_name,
            source="primary",
            salvage_trigger=None,
            primary_runner=args.primary,
            fallback_runner=args.fallback,
        )
        written += 1

    print(f"\nWrote {written} hybrid output(s) to {hybrid_dir}")

    # ------------------------------------------------------------------
    # Stage 5: compare against GV (optional)
    # ------------------------------------------------------------------
    all_rows: list[ComparisonRow] = []
    if not args.no_compare:
        print("\n=== Comparison ===")
        rows, cmp_failures = _compare_runner(
            hybrid_name, gv_subdir=gv_subdir, run_dir=hybrid_dir
        )
        all_rows.extend(rows)
        failures.extend(cmp_failures)
        _print_summary(hybrid_name, rows)

    # ------------------------------------------------------------------
    # Stage 6: persist
    # ------------------------------------------------------------------
    if not args.no_db:
        notes = args.notes or (
            f"hybrid primary={args.primary} fallback={args.fallback} "
            f"rule={args.salvage_rule!r} salvaged={len(salvage)}/{len(images)}"
        )
        insert_run_record(
            run_id=run_id,
            input_path=str(args.input.resolve()),
            runners=[hybrid_name],
            skipped_ocr=False,
            notes=notes,
            db_path=args.db,
        )
        if all_rows:
            insert_run(all_rows, db_path=args.db, run_id=run_id)
            print(
                f"\nWrote {len(all_rows)} comparison row(s) to {args.db} "
                f"(run_id={run_id})"
            )
        if failures:
            insert_failures(run_id, failures, db_path=args.db)
            print(f"Wrote {len(failures)} failure row(s) to {args.db}")

    if failures:
        print("\n=== Failures ===", file=sys.stderr)
        for runner, stem, stage, msg in failures:
            scope = f"{runner}/{stem}" if stem else runner
            print(f"  [{stage}] {scope}: {msg}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
