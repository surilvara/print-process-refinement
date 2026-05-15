# OCR Evaluation Metrics & Frontend Architecture

A reference for the concepts introduced while comparing PaddleOCR-VL and GLM-OCR against the Google Vision baseline, plus a proposed shape for a UI on top of this project.

---

## Part 1 — OCR evaluation metrics

We compare each runner's output to a Google Vision (GV) reference for the same image. The comparator emits one row per image with these columns. Lower is better for error rates; higher is better for overlap.

### Inputs to every metric

- **Reference (`ref_*`)** — what GV produced for the image.
- **Hypothesis (`hyp_*`)** — what the model under test produced.
- Both are reduced to a **list of text blocks**, each with a `text` string and a normalised bbox in `[0, 1]`, plus a concatenated `full_text` per image.

### 1. CER — Character Error Rate

**What it measures:** how much the model's text differs from the reference, counted in characters.

**Formula:**

$$
\text{CER} = \frac{\text{edit\_distance(ref, hyp)}}{\text{len(ref)}}
$$

`edit_distance` = minimum number of single-character insertions, deletions, and substitutions to turn `hyp` into `ref` (Levenshtein distance).

**Reading values:**

- `0.00` = identical text.
- `0.05` = ~5% of characters need fixing — typical for a healthy OCR model on clean print.
- `> 0.20` = poor quality.
- `> 1.0` = the hypothesis is *longer than* the reference and very different — often means the **reference is incomplete**, not that the model is broken.

**Limitation:** CER lumps three different errors together — substitutions (`0` → `O`), deletions (whole words missed), and insertions (hallucinated text). The headline number can't tell them apart.

**Useful derived value:** `total_edits ≈ CER × ref_chars` gives the absolute number of edit operations, which is more intuitive than a percentage for small documents.

### 2. WER — Word Error Rate

**What it measures:** same idea as CER but the unit is a whitespace-separated word.

**Formula:**

$$
\text{WER} = \frac{\text{edit\_distance(ref\_words, hyp\_words)}}{\text{len(ref\_words)}}
$$

**Reading values:**

- Usually 1.2–1.6× the CER on the same document (one wrong character per word usually destroys the whole word at the word level).
- More tolerant of whitespace/casing variations *between* words; less tolerant *within* words.

**When CER and WER diverge** — if WER is much higher than CER, the model is making many small per-word errors. If WER is similar to CER, errors cluster into a few badly-OCR'd regions.

### 3. Block count and delta

**What it measures:** how the model **segments** the page into regions.

- `ref_block_count` — number of blocks in GV's `fullTextAnnotation`.
- `hyp_block_count` — number of `OcrBlock` entries the runner produced.
- `block_count_delta = hyp_block_count − ref_block_count`.

**Reading values:**

- **Negative delta** = the model **under-segmented** — merged paragraphs/columns into single blocks. Common with VLMs that prefer big regions.
- **Positive delta** = the model **over-segmented** — split a paragraph into many lines. Common with line-based OCRs (like raw Tesseract).
- Zero is *not* automatically good — GV sometimes splits one column of body text into multiple blocks where downstream NER would prefer a single block.

**Why we track it:** downstream pipeline stages treat each block as a unit. Merging two paragraphs means:

- Their text is concatenated before NER → unrelated brand mentions can end up "in the same context".
- They share a layout label → a headline that gets merged into a body paragraph inherits the wrong type.
- The page-classification heuristic (ad vs editorial) uses block ratios, so very different counts skew the result.

**Block count is a sanity check, not a verdict.** Always read it alongside IoU.

### 4. Mean IoU — Intersection over Union of block bboxes

**What it measures:** how well the model's block bounding boxes **spatially align** with GV's blocks.

**Per-pair formula** (for two boxes A and B):

$$
\text{IoU}(A, B) = \frac{|A \cap B|}{|A \cup B|}
$$

- Numerator = area of overlap.
- Denominator = area of the union = `area(A) + area(B) − overlap`.
- Range: `0` (no overlap) → `1` (identical boxes).

**How `mean_iou` is computed:**

1. For each block in the reference, find the hypothesis block with the highest IoU (greedy match — one hypothesis box can serve multiple reference boxes).
2. Average those best-match IoUs across all reference blocks.

**Reading values:**

| IoU | Interpretation |
|---|---|
| > 0.9 | near-perfect block alignment |
| 0.7 – 0.9 | good — blocks line up with small offsets |
| 0.5 – 0.7 | decent — clear overlap but noticeable misalignment |
| 0.3 – 0.5 | poor — blocks are roughly in the right area but boundaries differ a lot |
| < 0.3 | bad — the model's boxes are in the wrong place or grossly misshapen |

**Why it complements block count:** block count says *how many* regions exist; IoU says *whether they're in the right place*. A model can produce the right number of blocks but in the wrong positions (high count match, low IoU), or merge several reference blocks into one giant box that only partly overlaps each (low count, low IoU).

**Limitation:** greedy matching can hide some segmentation errors — a merged 2-paragraph hypothesis box may still match the larger reference box with decent IoU. And IoU treats every block equally, so a tiny page-number block counts the same as a full body column.

### 5. Character delta — `ref_chars − hyp_chars`

**What it measures:** the **net length difference** between reference and hypothesis text.

This is the cleanest signal for **"how much information went missing"**:

- Positive delta = the model captured less text than GV.
- Negative delta = the model captured more text than GV (often because GV missed text the model found — i.e., GV is the one with the problem).

**Why it's useful:** CER counts substitutions too, so a model can have low CER but still drop chunks of text. The raw length delta isolates volume from accuracy.

**Limitation:** doesn't tell you *which* text was missed — could be one big region or many small drops scattered around.

---

## How to read the results table holistically

When you see a row, ask these questions in order:

1. **Is the baseline trustworthy?** If `hyp_chars` is wildly larger than `ref_chars` and both models agree closely with each other, GV missed something. Re-export GV before drawing conclusions.
2. **How accurate is the text?** Use CER as the primary number, WER as the secondary. Below 0.08 is good for print scans.
3. **How much was missed?** Use `ref_chars − hyp_chars`. If it's tiny (< 5% of `ref_chars`), the model is capturing nearly everything and CER reflects mostly character substitutions, not missing content.
4. **How well is the page segmented?** Use IoU first, block count second. IoU > 0.6 with a small block-count delta means the layout is usable.
5. **Are the models agreeing or disagreeing?** Two independent runners reaching the same answer is strong evidence the answer is right, even when it disagrees with GV.

---

## Part 2 — A theoretical frontend on top of this project

The repo is currently structured around two sibling sub-projects: `open_src/` (the production pipeline) and `ocr_eval/` (the evaluation harness). Adding a UI is feasible without a heavy refactor.

### Why the current structure is UI-friendly

- **Clean CLI boundaries.** Every stage has explicit args: `runners/<name>/run.py --input <file> --output <json>`, `compare.py --runner <name>`, `open_src/main.py --input <path> | --from-ocr <path>`. The UI can shell out to these or import the Python functions directly.
- **JSON-serialisable schemas.** `OcrOutput`, `OcrBlock`, `ImageRegion`, `BBox`, and the pipeline's `DocumentResult` / `PageResult` are dataclasses with `.save()` / `.load()`. Easy to send over HTTP or render in a browser.
- **Pluggable backend registries.** `OCR_BACKENDS`, `NER_BACKENDS`, etc. in `pipeline.py` are just dicts — a UI dropdown of available models is `list(OCR_BACKENDS.keys())`. Eval runners are discoverable by globbing `ocr_eval/runners/*/run.py`.
- **Persistent results.** `ocr_eval/results.db` and `open_src/database/results.db` already store every run. The UI can read them directly and show recent activity without recomputing.
- **`--from-ocr` decoupling.** Lets the UI re-run only the downstream stages against a frozen OCR snapshot — the cheap interactive loop for tuning NER / classification.

### Recommended placement: a new top-level `app/`

```
print_document_process_refinement/
├── open_src/              # production pipeline (existing)
├── ocr_eval/              # eval harness (existing)
├── inputs/                # source images (existing)
├── dmr_monitored_brands.csv
│
├── app/                   # NEW — UI + backend
│   ├── pyproject.toml     # gradio, fastapi, uvicorn, httpx
│   ├── README.md
│   ├── main.py            # Gradio entrypoint
│   ├── services/
│   │   ├── runners.py     # discover & invoke ocr_eval/runners/*
│   │   ├── pipeline.py    # invoke open_src/main.py --from-ocr ...
│   │   ├── mlx_servers.py # ensure_running() for :8111, :8112
│   │   └── results.py     # read SQLite DBs in read-only mode
│   ├── views/             # gradio Blocks: ocr_view, compare_view, pipeline_view
│   └── static/            # any js/css if needed
│
└── scripts/               # existing — start_mlx_server.sh etc.
```

**Why a peer, not a child of `ocr_eval/`:**

- Keeps `ocr_eval/` minimal and single-purpose.
- The app is a *consumer* of both `open_src/` and `ocr_eval/`, not part of either.
- Avoids polluting the eval venvs with web-framework dependencies.

**Why one new dir, not two (`frontend/` + `backend/`):**

- Gradio gives you both in one process for an MVP.
- Split into separate dirs only if you outgrow Gradio and move to React.

### How the app talks to the rest of the project

It **shells out**. Each runner has its own venv (`ocr_eval/runners/<name>/.venv/bin/python`), and the pipeline has its own (`open_src/.venv/`). The app's tiny venv just calls them as subprocesses:

```python
# app/services/runners.py
def run_ocr(runner: str, image: Path, output: Path) -> None:
    venv_python = RUNNERS_DIR / runner / ".venv" / "bin" / "python"
    run_script = RUNNERS_DIR / runner / "run.py"
    subprocess.run(
        [str(venv_python), str(run_script),
         "--input", str(image), "--output", str(output)],
        check=True,
    )
```

This means **no Python-level imports across project boundaries**. The app stays small and fast to install, and changes inside `open_src/` or `ocr_eval/` can't break the UI's environment.

### MLX server orchestration

The model servers run **outside** the app process:

- PaddleOCR-VL → MLX server on `:8111`, loads `PaddleOCR-VL-1.5-bf16`.
- GLM-OCR → MLX server on `:8112`, loads `GLM-OCR-bf16`.

The browser cannot start processes, so the app's backend handles it:

```python
def ensure_mlx_server(port: int, start_script: Path) -> None:
    if _port_is_open("localhost", port):
        return  # already running
    subprocess.Popen([str(start_script)], start_new_session=True)
    _wait_until_open(port, timeout=120)  # ~30s cold start
```

Called before invoking the matching runner. Both servers can run simultaneously (each loads ~5–8 GB of weights). Keep them warm — don't try to start/stop per request, the user-facing latency hit isn't worth it.

### Minimal first slice (one afternoon's work)

A single `app/main.py` Gradio Blocks app with three tabs:

1. **OCR** — dropdown of runners, file/folder picker scoped to `inputs/`, "Run" button. Shows the resulting JSON and a bbox overlay on the original image.
2. **Compare** — pick a runner, view the `latest_comparison` table from `ocr_eval/results.db`. Optionally show side-by-side text diff between hypothesis and GV.
3. **Pipeline** — pick a folder of OCR snapshots from `ocr_eval/outputs/<runner>/`, invoke `open_src/main.py --from-ocr <path>`, show entities and detections per page.

All three tabs talk to `services/` which shells out to existing CLIs. **No changes needed to `open_src/` or `ocr_eval/`** to get the MVP working.

### Gaps to fill before scaling beyond MVP

1. **Job state model.** OCR can take seconds to minutes. Need run IDs, status (queued / warming / running / done / failed), and either streaming logs or a polling endpoint. For one user, a dict in memory + `asyncio.subprocess` is fine; for multiple users, use a queue like RQ.
2. **Runner manifest.** Right now each runner's port and start script are conventions, not declared metadata. Add a `runner.json` next to each `run.py`:
   ```json
   { "name": "paddleocr_vl",
     "display_name": "PaddleOCR-VL 1.5",
     "venv": ".venv",
     "entrypoint": "run.py",
     "mlx_server": { "port": 8111, "start_script": "../scripts/start_mlx_server.sh" } }
   ```
   so `services/runners.py` doesn't hard-code anything.
3. **Path sandboxing.** Constrain user-provided paths to `inputs/` and `ocr_eval/outputs/`. Fine for localhost dev, essential before exposing the UI to anything else.
4. **Cold start UX.** First request after the MLX server is dead spends ~30s loading weights. Surface a "model warming up" state, not just an opaque "running" spinner.
5. **Schema convergence (optional).** `ocr_eval/schema.py` and `open_src/src/models/base.py` have nearly-identical dataclasses. Long-term, make one the source of truth (the eval schema is the more general one) and have the pipeline convert from it. Not blocking — `open_src/src/pipeline.py` already does this conversion in `_classified_blocks_from_ocr`.

### When to outgrow Gradio

Stay with Gradio while:

- You're the only user.
- The UI is "pick options → run → see result" with minimal client-side state.
- Auth, multi-user collaboration, and custom visualisations aren't required.

Move to FastAPI + React when:

- You need fine-grained UI components Gradio can't express (e.g. an interactive bbox editor on top of a high-res scan).
- Multiple people use it concurrently and need separate result views.
- You want to deploy to a server with proper auth, rate limits, and SSE/websocket streaming.

When that happens, promote `app/services/` to `app/backend/` (FastAPI), add `app/frontend/` (Vite + React), and the same architectural boundaries hold — the backend still shells out to the runners and the pipeline.
