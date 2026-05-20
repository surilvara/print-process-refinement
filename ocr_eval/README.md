# OCR Evaluation Harness

Compare different OCR models against a Google Vision baseline on a fixed set
of print-media scans. Results are persisted to SQLite for trend tracking.

## Goals

- Bake-off across multiple OCR backends without polluting the production
  pipeline in `open_src/`.
- Isolate each model in its own Python environment so dependency conflicts
  (`transformers` pin clashes etc.) never block evaluation.
- Produce comparable, diffable JSON output and a queryable history.

## Directory layout

```
ocr_eval/
├── paths.py               Canonical directory locations (edit here to move things)
├── schema.py              Normalised OCR output schema (OcrOutput, OcrBlock, BBox)
├── gvision_loader.py      Google Vision JSON → OcrOutput
├── metrics.py             CER, WER, block-count delta, mean bbox IoU
├── evaluate.py            Orchestrator: run N runners + compare under one run_id
├── compare.py             Single-runner compare (kept for tight inner loops)
├── db.py                  SQLite store: runs, comparisons, run_failures
├── runner_utils.py        Shared helpers (sys.path injection, image_size, folder iter)
├── results.db             SQLite history (created on first compare)
├── pyproject.toml         Harness deps: rapidfuzz, Pillow
│
├── googlevision_outputs/  Drop GV JSON baselines here (subfolders OK)
├── outputs/<runner>/      Each runner writes normalised JSON here
└── runners/
    ├── _template/         Copy this to add a new model
    ├── paddleocr_vl/      Converter for existing open_src/ pipeline output
    └── glm_ocr/           Local GLM-OCR via mlx-vlm + PP-DocLayoutV3
```

## Module responsibilities

| Module             | Used by                | Purpose                                           |
|--------------------|------------------------|---------------------------------------------------|
| `schema.py`        | everyone               | Single shape for OCR output across all runners    |
| `paths.py`         | compare, evaluate, runners | Where things live on disk                     |
| `runner_utils.py`  | every runner           | `sys.path` setup, `image_size()`, folder iter     |
| `gvision_loader.py`| compare, evaluate      | Parse `fullTextAnnotation` → blocks               |
| `metrics.py`       | compare, evaluate      | CER / WER / IoU / block delta                     |
| `db.py`            | compare, evaluate      | `runs`, `comparisons`, `run_failures` tables      |
| `compare.py`       | CLI                    | Single-runner compare; writes one row to `runs`   |
| `evaluate.py`      | CLI                    | Orchestrator: runs N runners + compare under one `run_id` |

If you find yourself duplicating code in two runners, add it to
`runner_utils.py` instead.

## End-to-end workflow

### 1. Drop the Google Vision baselines

Place each baseline JSON under `googlevision_outputs/`. The filename stem
must match the source image stem so the comparator can pair them.

```
inputs/vogue_uk_2026-04-01/00000041.jpg
ocr_eval/googlevision_outputs/10800084/00000041.json   ← stem must match
```

Subfolders are fine — `compare.py` searches recursively. Filenames longer
than the image stem are also supported as long as the stem appears as a
trailing component (e.g. `10800084_42524659_00000041.json` pairs with
`00000041.jpg`).

### 2. Run OCR + compare in one command (recommended)

`evaluate.py` runs every requested OCR model over a folder of images and
compares each against the GV baseline. All comparison rows and any
OCR-stage failures are persisted under a single `run_id`, so you can
query the whole evaluation as one unit.

```bash
cd ocr_eval

# Run every discovered runner on a publication folder
uv run python evaluate.py --input ../inputs/vogue_uk_2026-04-01/ --all

# Or pick specific runners (repeatable)
uv run python evaluate.py -i ../inputs/vogue_uk_2026-04-01/ \
  --runner paddleocr_vl --runner glm_ocr

# Skip OCR — just (re)compare whatever is already in outputs/<runner>/
uv run python evaluate.py --skip-ocr --all

# Skip the DB write entirely
uv run python evaluate.py -i ../inputs/foo/ --all --no-db
```

Each runner is invoked exactly once as a subprocess against its own venv
(`runners/<name>/.venv/bin/python run.py --input <folder> --output-dir
outputs/<name>`), so the model loads **once** per runner and is reused
across every image in the folder.

A runner-wide failure (missing venv, model load crash) is recorded in
`run_failures` and the orchestrator continues with the remaining runners.

### 3. Single-runner compare (legacy)

Still supported for tight inner loops on one model:

```bash
cd ocr_eval
uv run python compare.py --runner paddleocr_vl
```

It allocates its own `run_id` and writes one row to `runs`. Use the
orchestrator above when you want multiple runners grouped together.

### 4. Query the history

```bash
# Most recent eval per runner
sqlite3 ocr_eval/results.db \
  "SELECT runner, image_stem, cer, wer, mean_iou
   FROM latest_comparison ORDER BY runner, image_stem;"

# All runners that participated in a single evaluation
sqlite3 ocr_eval/results.db \
  "SELECT run_id, started_at, runners, skipped_ocr, notes
   FROM runs ORDER BY started_at DESC LIMIT 10;"

# Side-by-side metrics for one run_id
sqlite3 ocr_eval/results.db \
  "SELECT runner, image_stem, cer, wer, mean_iou
   FROM comparisons WHERE run_id='20260518T104348Z'
   ORDER BY image_stem, runner;"

# OCR-stage failures for a given run
sqlite3 ocr_eval/results.db \
  "SELECT runner, image_stem, stage, error_message
   FROM run_failures WHERE run_id='20260518T104348Z';"

# History of a single image
sqlite3 ocr_eval/results.db \
  "SELECT run_id, runner, cer, wer
   FROM comparisons WHERE image_stem='00000041'
   ORDER BY run_id;"
```

## Running a specific model

### PaddleOCR-VL

Two paths. Pick whichever fits your workflow:

**(A) Standalone runner** — runs PaddleOCR-VL directly. Independent of
`open_src/`. Uses the shared MLX server on port 8111.

```bash
# One-time:
cd ocr_eval/runners/paddleocr_vl && chmod +x setup.sh && ./setup.sh

# Single image:
.venv/bin/python run.py \
  --input ../../../inputs/vogue_uk_2026-04-01/00000041.jpg \
  --output ../../outputs/paddleocr_vl/00000041.json

# Folder of images (model loads once, loops internally):
.venv/bin/python run.py \
  --input ../../../inputs/vogue_uk_2026-04-01/ \
  --output-dir ../../outputs/paddleocr_vl/
```

**(B) Converter** — translates existing `open_src/` pipeline output into the
normalised schema. No model re-run, no separate venv.

```bash
cd ocr_eval
uv run python runners/paddleocr_vl/convert.py \
  --pipeline-output ../open_src/output/vogue_uk_2026-04-01_20260506T114730/
```

Both paths write to `outputs/paddleocr_vl/<stem>.json`. Full details:
[runners/paddleocr_vl/README.md](runners/paddleocr_vl/README.md).

### GLM-OCR (local mlx-vlm server)

Self-hosted on Apple Silicon. Layout via PP-DocLayoutV3 + per-region
recognition via `mlx-community/GLM-OCR-bf16`.

One-time setup:

```bash
cd ocr_eval/runners/glm_ocr
chmod +x setup.sh start_server.sh
./setup.sh
```

Each run (two terminals):

```bash
# Terminal 1 — leave running
cd ocr_eval/runners/glm_ocr && ./start_server.sh

# Terminal 2 — single image
cd ocr_eval/runners/glm_ocr
.venv/bin/python run.py \
  --input ../../../inputs/vogue_uk_2026-04-01/00000041.jpg \
  --output ../../outputs/glm_ocr/00000041.json

# Terminal 2 — folder of images (model loads once, loops internally)
.venv/bin/python run.py \
  --input ../../../inputs/vogue_uk_2026-04-01/ \
  --output-dir ../../outputs/glm_ocr/
```

Full details: [runners/glm_ocr/README.md](runners/glm_ocr/README.md).

## Adding a new runner

1. Copy the template:

   ```bash
   cp -r ocr_eval/runners/_template ocr_eval/runners/my_model
   ```

2. Implement `run.py` — replace the TODOs in `run(image_path)`. Emit blocks
   with bboxes in `[0, 1]` (use `BBox.from_vertices` or scale manually).

3. Install the model's deps in a venv local to the runner folder:

   ```bash
   cd ocr_eval/runners/my_model
   uv venv && VIRTUAL_ENV="$PWD/.venv" uv pip install -r requirements.txt
   ```

   (One venv per runner avoids cross-model `transformers`/`torch` conflicts.)

4. Run it against an image or a folder:

   ```bash
   # Single image
   .venv/bin/python run.py --input <img> --output ../../outputs/my_model/<stem>.json

   # Whole folder (model loads once)
   .venv/bin/python run.py --input <folder> --output-dir ../../outputs/my_model/
   ```

5. Compare (single runner) or evaluate with others under one `run_id`:

   ```bash
   cd ocr_eval
   uv run python compare.py --runner my_model

   # Or, alongside existing runners:
   uv run python evaluate.py -i ../inputs/<folder>/ --all
   ```

The orchestrator auto-discovers any `runners/<name>/run.py`. No comparator
or orchestrator changes needed when you add a new runner.

## Why separate venvs per runner?

PaddleOCR, glmocr, mlx-vlm, doctr each pin different `transformers` /
`paddlepaddle` / `torch` versions. One env causes silent breakage. Each
runner stays in `runners/<name>/.venv/` with its own deps and is invoked as
a subprocess. The comparator's deps stay minimal (`rapidfuzz`, `Pillow`).

## Metrics — what they mean

| Metric             | Interpretation                                            |
|--------------------|-----------------------------------------------------------|
| `cer`              | Char-level Levenshtein / len(reference text)              |
| `wer`              | Token-level Levenshtein / len(reference words)            |
| `mean_iou`         | For each GV block, best IoU with hyp blocks, averaged     |
| `ref_chars` / `hyp_chars` | Raw character counts (sanity check)                |

Text comparison normalises whitespace and case but **keeps punctuation** —
em-dashes, smart quotes etc. are real failure modes worth surfacing.

## Troubleshooting

- **`No paired files found`** — your GV JSON stems don't match any runner
  output stems. Check `ls ocr_eval/googlevision_outputs/**/*.json` and
  `ls ocr_eval/outputs/<runner>/*.json` — the stems must match (or the
  runner stem must be a trailing component of the GV stem).
- **`No runner output dir`** — the runner hasn't produced anything yet.
  Re-read "Running a specific model" above.
- **DB write warnings** — `db.py` is best-effort; JSON output is the source
  of truth. Delete `results.db` to start fresh; the schema is recreated on
  next write.
