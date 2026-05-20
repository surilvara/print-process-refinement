"""Gradio UI for the OCR evaluation harness.

Provides a local-only browser UI that wraps `evaluate.run_evaluation`:

    - Pick a publication folder under `inputs/` from a dropdown.
    - Select one or more discovered runners (or "All").
    - Watch a live progress bar update per processed image.
    - See per-runner duration + comparison metrics from SQLite after the
      run finishes.

OCR runners are executed sequentially (no parallel model loading) to avoid
GPU/CPU contention between models.

Usage:
    cd ocr_eval && uv run python app.py        # default port (7860)
    cd ocr_eval && uv run python app.py --port 7870
"""

from __future__ import annotations

import argparse
import queue
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import gradio as gr

from db import (
    DEFAULT_DB_PATH,
    fetch_ocr_runs_for_run_id,
)
from evaluate import (
    EvaluationResult,
    OcrRunRecord,
    _count_images,
    _discover_runners,
    run_evaluation,
)
from metrics import ComparisonRow
from paths import INPUTS_DIR
from runner_utils import IMAGE_EXTS

# ---------------------------------------------------------------------------
# Backend server preflight
# ---------------------------------------------------------------------------

_OCR_EVAL_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _OCR_EVAL_DIR.parent
_RUNNERS_DIR = _OCR_EVAL_DIR / "runners"

# Each entry describes the local HTTP server a runner depends on.
#   port:          TCP port to probe (host is always 127.0.0.1).
#   cli_name:      argument to `./scripts/mlx start <name>` to launch it.
#                  None ⇒ server is managed externally; we only surface a
#                  friendly error if it's down.
#   ready_timeout: seconds to wait for the port to open after launching.
_MLX_CLI: Path = _PROJECT_ROOT / "scripts" / "mlx"

_SERVER_SPECS: dict[str, dict] = {
    "glm_ocr": {
        "port": 8112,
        "cli_name": "glm",
        "ready_timeout": 180,
        "manual_hint": "./scripts/mlx start glm",
    },
    "paddleocr_vl": {
        "port": 8111,
        "cli_name": "paddle",
        "ready_timeout": 180,
        "manual_hint": "./scripts/mlx start paddle",
    },
}

# Track servers we launched so we don't spawn duplicates if Run is clicked
# again within the same app session.
_LAUNCHED_SERVERS: dict[str, subprocess.Popen] = {}


def _port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    """Return True if a TCP connect to (host, port) succeeds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _launch_server(runner: str, spec: dict) -> None:
    """Delegate startup to `./scripts/mlx start <cli_name>`.

    The CLI handles logging, idempotency, and waiting for the port itself,
    so we just fire-and-forget here. start_new_session=True detaches the
    process so the server survives if this app exits.
    """
    if not _MLX_CLI.is_file():
        raise RuntimeError(f"mlx CLI not found at {_MLX_CLI}")
    cli_name = spec.get("cli_name")
    if not cli_name:
        raise RuntimeError(f"{runner}: no cli_name configured")
    proc = subprocess.Popen(
        ["bash", str(_MLX_CLI), "start", cli_name],
        cwd=str(_PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    _LAUNCHED_SERVERS[runner] = proc


def _wait_for_port(port: int, timeout: float) -> bool:
    """Poll the port up to `timeout` seconds; return True when it opens."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _port_open(port):
            return True
        time.sleep(1.0)
    return False


def _preflight_servers(runners: list[str]):
    """Yield status strings while bringing required servers up.

    Yields tuples of (message, ok) where ok is False on a fatal error.
    The final tuple has ok=True with message="" once all servers are ready.
    """
    for runner in runners:
        spec = _SERVER_SPECS.get(runner)
        if spec is None:
            continue  # runner has no known server dependency
        port = spec["port"]
        if _port_open(port):
            yield (f"`{runner}` server already up on port {port}.", True)
            continue

        if spec.get("cli_name") is None:
            yield (
                f"**{runner} server not reachable on port {port}** — "
                f"start it manually:\n\n```\n{spec['manual_hint']}\n```",
                False,
            )
            return

        # Auto-start path (currently only glm_ocr).
        if (
            runner not in _LAUNCHED_SERVERS
            or _LAUNCHED_SERVERS[runner].poll() is not None
        ):
            try:
                _launch_server(runner, spec)
            except Exception as exc:  # noqa: BLE001
                yield (f"Failed to launch `{runner}` server: {exc}", False)
                return
            yield (
                f"Launching `{runner}` server (port {port}) — "
                f"waiting up to {spec['ready_timeout']}s for it to be ready…",
                True,
            )
        else:
            yield (
                f"`{runner}` server launch already in progress — "
                f"waiting for port {port}…",
                True,
            )

        if not _wait_for_port(port, spec["ready_timeout"]):
            yield (
                f"**Timed out** waiting for `{runner}` server on port {port}. "
                f"Check `ocr_eval/runners/{runner}/logs/` for details.",
                False,
            )
            return
        yield (f"`{runner}` server is ready on port {port}.", True)

    yield ("", True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _list_input_folders() -> list[str]:
    """Sorted folder names under `inputs/` that contain image files."""
    if not INPUTS_DIR.is_dir():
        return []
    folders: list[str] = []
    for p in sorted(INPUTS_DIR.iterdir()):
        if not p.is_dir():
            continue
        # Only include folders that contain at least one supported image.
        if any(f.is_file() and f.suffix.lower() in IMAGE_EXTS for f in p.iterdir()):
            folders.append(p.name)
    return folders


def _summarise_rows(rows: list[ComparisonRow]) -> dict:
    """Aggregate ComparisonRows into mean metrics keyed by runner."""
    by_runner: dict[str, list[ComparisonRow]] = {}
    for r in rows:
        by_runner.setdefault(r.runner, []).append(r)
    out: dict[str, dict] = {}
    for runner, rs in by_runner.items():
        n = len(rs)
        out[runner] = {
            "n": n,
            "mean_cer": sum(r.cer for r in rs) / n,
            "mean_wer": sum(r.wer for r in rs) / n,
            "mean_iou": sum(r.mean_iou for r in rs) / n,
        }
    return out


def _format_results_table(result: EvaluationResult) -> list[list]:
    """Build the rows of the final results dataframe."""
    metrics = _summarise_rows(result.comparison_rows)
    # Use ocr_runs records to source duration; fall back to per-runner
    # presence in `runners` (for --skip-ocr there are no ocr_runs).
    duration_by_runner = {r.runner: r.duration_seconds for r in result.ocr_runs}
    images_by_runner = {r.runner: r.image_count for r in result.ocr_runs}
    table: list[list] = []
    for runner in result.runners:
        m = metrics.get(runner)
        table.append(
            [
                runner,
                images_by_runner.get(runner, m["n"] if m else 0),
                (
                    f"{duration_by_runner[runner]:.1f}s"
                    if runner in duration_by_runner
                    else "(skipped)"
                ),
                f"{m['mean_cer']:.4f}" if m else "n/a",
                f"{m['mean_wer']:.4f}" if m else "n/a",
                f"{m['mean_iou']:.4f}" if m else "n/a",
            ]
        )
    return table


def _format_failures(result: EvaluationResult) -> str:
    if not result.failures:
        return ""
    lines = ["**Failures:**"]
    for runner, stem, stage, msg in result.failures:
        scope = f"{runner}/{stem}" if stem else runner
        lines.append(f"- `[{stage}]` {scope}: {msg}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Background worker — runs the evaluation off the UI thread so progress
# events can stream back via a queue without blocking Gradio's generator.
# ---------------------------------------------------------------------------


class _Event:
    """Plain message passed from the worker thread to the UI generator."""

    __slots__ = ("kind", "payload")

    def __init__(self, kind: str, payload: object) -> None:
        self.kind = kind
        self.payload = payload


def _worker(
    input_path: Path,
    runners: list[str],
    notes: str | None,
    db_path: Path | None,
    out_q: "queue.Queue[_Event]",
) -> None:
    """Run the evaluation, pushing _Event messages into `out_q`."""

    def on_runner_start(runner: str, image_count: int) -> None:
        out_q.put(_Event("runner_start", (runner, image_count)))

    def on_image_start(runner: str, image: str) -> None:
        out_q.put(_Event("image_start", (runner, image)))

    def on_image(runner: str, image: str, completed: int) -> None:
        out_q.put(_Event("image", (runner, image, completed)))

    def on_runner_complete(runner: str, record: OcrRunRecord) -> None:
        out_q.put(_Event("runner_complete", record))

    try:
        result = run_evaluation(
            input_path=input_path,
            runners=runners,
            skip_ocr=False,
            db_path=db_path,
            notes=notes,
            on_image=on_image,
            on_image_start=on_image_start,
            on_runner_start=on_runner_start,
            on_runner_complete=on_runner_complete,
        )
        out_q.put(_Event("done", result))
    except Exception as exc:  # noqa: BLE001 - report to UI rather than crash
        out_q.put(_Event("error", f"{type(exc).__name__}: {exc}"))


# ---------------------------------------------------------------------------
# Gradio handler
# ---------------------------------------------------------------------------


_RESULTS_HEADERS = [
    "runner",
    "images",
    "duration",
    "mean CER",
    "mean WER",
    "mean IoU",
]


_COMPARISON_EXPLAINER = """
### In plain English

We treat **Google Vision OCR** as the ground-truth reference and ask: how
close did each runner come to producing the same text and laying out the
page the same way? Lower error rates and higher IoU mean the runner agrees
with Vision. Google Vision is mature and battle-tested, so it's a credible
yardstick — but it's still just another model, not perfect truth.

### The challenge

The two systems emit very differently-shaped JSON. Google Vision returns a
deeply nested tree of `pages → blocks → paragraphs → words → symbols`, each
symbol tagged with a `detectedBreak` (space, line break, hyphen, …).
PaddleOCR-VL returns a flat list of layout regions with one big chunk of
text per region (`block_content` + `block_bbox` + `block_label`).
Comparing them directly would be apples-to-oranges.

### The fix: a shared schema

Both outputs are converted into the same neutral structure — `OcrOutput`
with a list of `OcrBlock { text, bbox, confidence, block_type }` and a
reconstructed `full_text`. Bounding boxes are normalised to `[0, 1]` so
images of different sizes can be compared. Every metric runs on this
normalised shape, never on the raw JSON.

| Side | Native shape | Becomes one `OcrBlock` per… |
|---|---|---|
| Google Vision (reference) | `fullTextAnnotation.pages[0].blocks[].paragraphs[].words[].symbols[]` | paragraph; text is reassembled symbol-by-symbol respecting `detectedBreak` |
| PaddleOCR-VL (hypothesis) | `parsing_res_list[]` | layout region; `block_label` is mapped to our schema (e.g. `paragraph_title → subheadline`) |

Pages are paired by **filename stem** — `00000044.json` on the Vision side
lines up with `00000044.json` on the runner side. Anything unmatched is
reported as a warning.

### The three metrics

Each paired page produces one row of metrics:

| Metric | What it measures | How it's computed |
|---|---|---|
| **CER** (Character Error Rate) | Textual accuracy at the character level | Levenshtein distance between Vision's `full_text` and the runner's `full_text`, divided by reference length. Whitespace collapsed, lowercased; punctuation kept. |
| **WER** (Word Error Rate) | Textual accuracy at the word level | Same idea as CER but tokenised on whitespace. Useful when a single character error trashes one word but the rest is correct. |
| **Mean best-match IoU** | Spatial accuracy — does the runner draw boxes in the same places? | For each Vision paragraph box, find the runner box it overlaps most (intersection-over-union), then average those best scores. Asymmetric: "how well does the runner cover the reference?" Treat this as a regression detector, not an absolute quality score — Vision's paragraph boxes and Paddle's semantic-region boxes aren't defined the same way, so the absolute number is calibrated by your own historical baseline. |

CER/WER cap out at 1.0 (totally different texts); IoU runs 0–1 (1.0 = exact
overlap). Lower CER/WER and higher IoU are better. **CER and WER are the
headline quality signals**; IoU is a diagnostic for layout-detector health.

### What this comparison **can't** tell you

- **Reading order disagreements look like errors.** If the runner reads
  columns left-to-right but Vision reads top-to-bottom across columns, CER
  spikes even when every word is correct. We don't currently reorder
  blocks before computing CER.
- **Granularity mismatch is structural.** Vision emits ~paragraphs; the
  runner emits whatever its layout detector calls a region (often coarser).
  IoU's best-match design tolerates 1:N splits, but the absolute IoU
  number reflects this definitional mismatch as much as it reflects
  quality — which is why we no longer show block-count delta as a
  headline metric.
- **Block-type accuracy isn't measured.** Vision doesn't classify (no
  "headline" vs "body"), so we can't score type labels against it.
- **Vision is not ground truth.** It has its own errors — especially on
  decorative fonts, italics, tight kerning, and rotated text. A runner
  that "disagrees" with Vision may be more correct on that page.
- **Confidence scores aren't comparable.** Vision's confidence is averaged
  symbol confidence; PaddleOCR's is the layout-detector score (not a
  recognition score). Stored side-by-side, never aggregated.

### Where the numbers live

The aggregated per-runner row (above) is the mean across all paired
pages for the current run. The full per-page table is persisted to
`ocr_eval/results.db` (table `comparison_results`) — query it directly for
distribution analysis (e.g. which page IDs have the worst CER).
"""


def _empty_results_table() -> list[list]:
    return []


def _progress_bar_md(fraction: float, width: int = 28) -> str:
    """Render a unicode block progress bar inside a markdown string."""
    fraction = max(0.0, min(1.0, fraction))
    filled = int(round(fraction * width))
    bar = "█" * filled + "░" * (width - filled)
    return f"`{bar}` **{fraction * 100:5.1f}%**"


def run_handler(
    input_folder: str,
    selected_runners: list[str],
    notes: str,
    write_db: bool,
):
    """Streaming handler bound to the Run button.

    Yields tuples of UI updates matching the bound outputs:
      (status_md, results_table, failures_md, run_id_md)
    """
    if not input_folder:
        yield (
            "Pick an input folder first.",
            _empty_results_table(),
            "",
            "",
        )
        return
    if not selected_runners:
        yield (
            "Select at least one runner.",
            _empty_results_table(),
            "",
            "",
        )
        return

    input_path = INPUTS_DIR / input_folder
    if not input_path.is_dir():
        yield (
            f"Input folder not found: {input_path}",
            _empty_results_table(),
            "",
            "",
        )
        return

    total_images = _count_images(input_path)
    db_path = DEFAULT_DB_PATH if write_db else None

    # ---- Server preflight ----------------------------------------------
    # Make sure each selected runner's backend server is reachable before
    # we hand off to the worker thread. Auto-start where we can (glm_ocr);
    # surface a friendly error otherwise.
    progress_md = _progress_bar_md(0.0)
    status_lines: list[str] = []
    for message, ok in _preflight_servers(selected_runners):
        if message:
            status_lines.append(message)
            yield (
                f"{progress_md}\n\n" + "\n\n".join(status_lines),
                _empty_results_table(),
                "",
                "",
            )
        if not ok:
            return

    out_q: "queue.Queue[_Event]" = queue.Queue()
    worker = threading.Thread(
        target=_worker,
        args=(input_path, selected_runners, notes or None, db_path, out_q),
        daemon=True,
    )
    worker.start()

    current_runner: str | None = None
    completed_so_far = 0
    runners_done = 0
    total_runners = len(selected_runners)
    last_completed_image = ""
    current_image = ""

    yield (
        f"{_progress_bar_md(0.0)}\n\n"
        f"Starting evaluation: {total_runners} runner(s) × {total_images} image(s).",
        _empty_results_table(),
        "",
        "",
    )

    def _fraction() -> float:
        slice_per_runner = 1.0 / total_runners if total_runners else 1.0
        return min(
            runners_done * slice_per_runner
            + slice_per_runner * (completed_so_far / max(total_images, 1)),
            0.999,
        )

    # Pump events from the worker until it sends `done` or `error`.
    while True:
        ev = out_q.get()
        if ev.kind == "runner_start":
            current_runner, _ = ev.payload  # type: ignore[misc]
            completed_so_far = 0
            last_completed_image = ""
            current_image = ""
            yield (
                f"{_progress_bar_md(_fraction())}\n\n"
                f"**{runners_done}/{total_runners}** runners done — "
                f"now running **{current_runner}** (0/{total_images}).",
                _empty_results_table(),
                "",
                "",
            )
        elif ev.kind == "image_start":
            runner, image = ev.payload  # type: ignore[misc]
            current_image = image
            last_line = (
                f"✓ last completed: `{last_completed_image}`"
                if last_completed_image
                else "_no images completed yet_"
            )
            yield (
                f"{_progress_bar_md(_fraction())}\n\n"
                f"**{runners_done}/{total_runners}** runners done — "
                f"**{runner}**: {completed_so_far}/{total_images}  \n"
                f"▶ now processing: `{image}`  \n"
                f"{last_line}",
                _empty_results_table(),
                "",
                "",
            )
        elif ev.kind == "image":
            runner, image, completed = ev.payload  # type: ignore[misc]
            completed_so_far = completed
            last_completed_image = image
            yield (
                f"{_progress_bar_md(_fraction())}\n\n"
                f"**{runners_done}/{total_runners}** runners done — "
                f"**{runner}**: {completed}/{total_images}  \n"
                f"✓ last completed: `{image}`",
                _empty_results_table(),
                "",
                "",
            )
        elif ev.kind == "runner_complete":
            record: OcrRunRecord = ev.payload  # type: ignore[assignment]
            runners_done += 1
            completed_so_far = 0
            yield (
                f"{_progress_bar_md(runners_done / total_runners if total_runners else 1.0)}\n\n"
                f"**{runners_done}/{total_runners}** runners done — "
                f"`{record.runner}` finished in "
                f"{record.duration_seconds:.1f}s (exit {record.exit_code}).",
                _empty_results_table(),
                "",
                "",
            )
        elif ev.kind == "error":
            yield (
                f"{_progress_bar_md(_fraction())}\n\n" f"**Error:** {ev.payload}",
                _empty_results_table(),
                "",
                "",
            )
            return
        elif ev.kind == "done":
            result: EvaluationResult = ev.payload  # type: ignore[assignment]
            yield (
                f"{_progress_bar_md(1.0)}\n\n"
                f"**Done.** run_id = `{result.run_id}` — "
                f"{len(result.comparison_rows)} comparison row(s) "
                f"across {len(result.runners)} runner(s).",
                _format_results_table(result),
                _format_failures(result),
                f"run_id: `{result.run_id}`  •  "
                f"db: `{DEFAULT_DB_PATH if write_db else '(not written)'}`",
            )
            return


# ---------------------------------------------------------------------------
# UI definition
# ---------------------------------------------------------------------------


def build_ui() -> gr.Blocks:
    discovered_runners = _discover_runners()
    folders = _list_input_folders()

    with gr.Blocks(title="OCR evaluation harness") as demo:
        gr.Markdown(
            "# OCR evaluation harness\n"
            "Pick an input publication folder and one or more OCR runners. "
            "Runners execute **sequentially** to avoid GPU/CPU contention. "
            "Comparison against the Google Vision baseline runs automatically."
        )

        with gr.Row():
            with gr.Column(scale=1):
                input_folder = gr.Dropdown(
                    label="Input folder (inputs/)",
                    choices=folders,
                    value=folders[0] if folders else None,
                    interactive=True,
                )
                refresh_btn = gr.Button("↻ Refresh folder list", size="sm")
                selected_runners = gr.CheckboxGroup(
                    label="Runners",
                    choices=discovered_runners,
                    value=discovered_runners,  # default: all selected
                    interactive=True,
                )
                notes = gr.Textbox(
                    label="Notes (optional)",
                    placeholder="Free-text note attached to the run record.",
                    lines=1,
                )
                write_db = gr.Checkbox(
                    label="Write results to SQLite",
                    value=True,
                )
                run_btn = gr.Button("Run", variant="primary")

            with gr.Column(scale=2):
                status_md = gr.Markdown("Ready.", label="Status")
                results_table = gr.Dataframe(
                    headers=_RESULTS_HEADERS,
                    label="Per-runner results",
                    value=_empty_results_table(),
                    interactive=False,
                    wrap=True,
                )
                failures_md = gr.Markdown("", label="Failures")
                run_id_md = gr.Markdown("", label="Run ID")

        with gr.Accordion("How the comparison works", open=False):
            gr.Markdown(_COMPARISON_EXPLAINER)

        def _refresh() -> "gr.Dropdown":
            new_folders = _list_input_folders()
            return gr.Dropdown(
                choices=new_folders,
                value=new_folders[0] if new_folders else None,
            )

        refresh_btn.click(_refresh, outputs=input_folder)

        run_btn.click(
            run_handler,
            inputs=[input_folder, selected_runners, notes, write_db],
            outputs=[status_md, results_table, failures_md, run_id_md],
            show_progress="hidden",
        )

    return demo


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Port to bind the local Gradio server (default: 7860).",
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="Expose a public Gradio share link (NOT recommended; local-only by default).",
    )
    args = parser.parse_args()

    demo = build_ui()
    demo.queue()  # required so generator-based handlers stream updates
    demo.launch(
        server_name="127.0.0.1",
        server_port=args.port,
        share=args.share,
        inbrowser=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
