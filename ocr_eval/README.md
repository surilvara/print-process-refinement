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
├── compare.py             Per-image table + summary + SQLite write
├── db.py                  SQLite store (best-effort)
├── runner_utils.py        Shared helpers (sys.path injection, image_size)
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
| `paths.py`         | compare, runners       | Where things live on disk                         |
| `runner_utils.py`  | every runner           | `sys.path` setup + `image_size()`                 |
| `gvision_loader.py`| compare                | Parse `fullTextAnnotation` → blocks               |
| `metrics.py`       | compare                | CER / WER / IoU / block delta                     |
| `db.py`            | compare                | Append rows to `results.db`                       |

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

### 2. Produce normalised output for the runner(s) you want to test

See **Running a specific model** below.

### 3. Compare and persist

```bash
cd ocr_eval
uv run python compare.py --runner paddleocr_vl
uv run python compare.py --runner glm_ocr
```

Each invocation:
- Prints a per-image table + summary.
- Appends rows to `results.db` (tagged with a UTC `run_timestamp`).
- Optionally writes a CSV with `--csv path/to/file.csv`.

Skip the DB write with `--no-db`.

### 4. Query the history

```bash
# Latest result per runner per image
sqlite3 ocr_eval/results.db \
  "SELECT runner, image_stem, cer, wer, mean_iou
   FROM latest_comparison ORDER BY runner, image_stem;"

# Mean metrics across the latest run for each runner
sqlite3 ocr_eval/results.db \
  "SELECT runner,
          ROUND(AVG(cer),4)      AS mean_cer,
          ROUND(AVG(wer),4)      AS mean_wer,
          ROUND(AVG(mean_iou),4) AS mean_iou,
          COUNT(*)               AS n
   FROM latest_comparison GROUP BY runner;"

# History of a single image
sqlite3 ocr_eval/results.db \
  "SELECT run_timestamp, runner, cer, wer
   FROM comparisons WHERE image_stem='00000041'
   ORDER BY run_timestamp;"
```

## Running a specific model

### PaddleOCR-VL

Two paths. Pick whichever fits your workflow:

**(A) Standalone runner** — runs PaddleOCR-VL directly. Independent of
`open_src/`. Uses the shared MLX server on port 8111.

```bash
# One-time:
cd ocr_eval/runners/paddleocr_vl && chmod +x setup.sh && ./setup.sh

# Then for each image:
.venv/bin/python run.py \
  --input ../../../inputs/vogue_uk_2026-04-01/00000041.jpg \
  --output ../../outputs/paddleocr_vl/00000041.json
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

# Terminal 2 — invoke the runner per image
cd ocr_eval/runners/glm_ocr
.venv/bin/python run.py \
  --input ../../../inputs/vogue_uk_2026-04-01/00000041.jpg \
  --output ../../outputs/glm_ocr/00000041.json
```

To loop over a folder:

```bash
cd ocr_eval/runners/glm_ocr
for img in ../../../inputs/vogue_uk_2026-04-01/*.jpg; do
  stem=$(basename "$img" .jpg)
  .venv/bin/python run.py --input "$img" --output "../../outputs/glm_ocr/${stem}.json"
done
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

4. Run it against an image:

   ```bash
   .venv/bin/python run.py --input <path> --output ../../outputs/my_model/<stem>.json
   ```

5. Compare:

   ```bash
   cd ocr_eval && uv run python compare.py --runner my_model
   ```

The harness will create `outputs/my_model/` and a new row in `results.db`
the first time it sees the runner. No comparator changes needed.

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
| `block_count_delta`| `len(hyp.blocks) − len(ref.blocks)` (negative = under-segmenting) |
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
