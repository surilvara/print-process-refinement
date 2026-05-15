# Project Summary — Print Document Intelligence Pipeline

## What this project is

A modular Python pipeline that ingests scanned print media (newspaper/magazine images and PDFs) and produces a structured JSON describing what is on each page: the text that was printed, what kind of text block it is (headline, body, caption, etc.), the named entities mentioned (people, brands, places…), and the objects detected in the photographs/illustrations on the page.

The system is tuned for the **beauty and fashion** publishing domain — its zero-shot vision prompts and entity remappings (e.g. `ORG → BRAND`) reflect that focus.

## What it produces

For each input file the pipeline writes one JSON document to `output/` with this shape:

- `metadata` — input filename, ISO timestamp, models used, pipeline version, and (when applicable) `publication: {name, magazine_name, issue_date, source_path, page_label, total_pages}`
- `pages[]` — for each page:
  - `classification` — `'editorial'` or `'advertising'`, plus `classification_reason`
  - `text_blocks[]` — id, type (`headline` / `subheadline` / `body` / `caption` / `byline` / `advertisement_copy` / `other`), recognised text, normalised bbox, extracted entities
  - `image_regions[]` — id, bbox on the page, and OWLv2 detections (label, confidence, bbox inside the crop)
- `document` — aggregated counts: every entity with frequency, every detection label with frequency, total page count
- `errors` — any per-page failures captured during the run

Output filenames follow `<input_stem>_<timestamp>_<model_slug>.json`.

Each successful run is also mirrored into a SQLite DB (default `database/results.db`) for cross-run querying — see [SQLite mirror](#sqlite-mirror) below.

## Pipeline stages

```
Input (JPG/PNG/PDF)
  │
  ▼
[1] OCR + page segmentation  →  text blocks + image-region crops
  │
  ├──► [2a] Layout classification  →  block type per text block
  │
  ├──► [2b] Named entity recognition  →  entities per text block
  │
  └──► [3] Zero-shot image analysis  →  detections per image region
                       │
                       ▼
                  JSON output
```

### Stage 1 — OCR + page segmentation

Two interchangeable backends are registered:

- **PP-StructureV3** (`paddleocr`) — *default in `config.yaml`*. Handles OCR **and** layout in a single pass; the same instance is reused for stages 1 and 2a. Maps PaddleOCR's native block labels (`doc_title`, `paragraph_title`, `figure_caption`, …) onto the pipeline's schema.
- **DocTR** (`python-doctr`) — text detection (`db_resnet50`) + recognition (`crnn_vgg16_bn`). Image regions are derived heuristically: a binary mask of all word boxes is inverted, then OpenCV connected-components extracts the large non-text blobs (filtered by area ratio and aspect).

### Stage 2a — Layout classification

`LayoutLMv3Layout` tries to load `microsoft/layoutlmv3-base` as a token-classification model. If that fails (the base model has no classification head out of the box), it falls back to a **geometry-based heuristic**: relative line height + vertical position + word count + keyword cues decide between headline, subheadline, caption, byline, body. With the PP-Structure backend, classifications already came out of stage 1 and `classify()` simply returns them.

### Stage 2b — Named entity recognition

`SpacyNER` runs `en_core_web_trf` on each block's text. Entity labels are passed through a remapping dict from config — the default config rewrites `ORG → BRAND` so brand mentions are first-class in the output.

### Stage 3 — Image analysis

`OWLv2ImageAnalysis` runs `google/owlv2-base-patch16-ensemble` as a zero-shot detector. The text prompts come from `config.yaml` and are grouped into people / logos / fashion_beauty / advertising buckets but are flattened into one prompt list at call time. Stage failure is non-fatal — if OWLv2 throws, the pipeline logs it and emits empty detections so text results still ship.

## Architecture

Each stage sits behind an abstract base class in `src/models/base.py` (`OCRModel`, `LayoutModel`, `NERModel`, `ImageAnalysisModel`) with a small set of frozen dataclasses (`TextBlock`, `ClassifiedTextBlock`, `Entity`, `ImageRegion`, `Detection`, `PageResult`, `DocumentResult`). All bounding boxes are normalised to `[0, 1]`.

`src/pipeline.py` wires concrete implementations into per-stage **registries** keyed by backend name:

```
OCR_BACKENDS              = { "doctr": DocTROCR, "ppstructure": PPStructureBackend }
LAYOUT_BACKENDS           = { "layoutlmv3": LayoutLMv3Layout, "ppstructure": PPStructureBackend }
NER_BACKENDS              = { "spacy": SpacyNER }
IMAGE_ANALYSIS_BACKENDS   = { "owlv2": OWLv2ImageAnalysis }
```

Adding a new backend = implement the interface and register it in the dict.

`Pipeline.run(input_path)` → resolves files → loads all models once → for each file: render pages → process each page through stages → write JSON → mirror to SQLite (best-effort) → move the original file to a sibling `processed/` directory.

## Inputs and publications

`src/input_handler.resolve_inputs` walks the path passed via `--input` and returns a flat list of `InputItem`s in processing order.

- A **file** path → one standalone item.
- A **directory** → one level deep walk:
  - Files directly inside the directory become standalone items (no publication).
  - Each subdirectory becomes a **publication**: its supported files are sorted alphabetically and assigned `page_label` `"1"`, `"2"`, … . The publication's identity is the subdirectory's basename. The basename is also parsed for `magazine_name` + `issue_date` (see below).

Example layout:

```
inputs/
├── loose_scan.jpg               ← standalone
├── Vogue_2026-04-15/            ← magazine "Vogue", date 2026-04-15
│   ├── 01_cover.jpg
│   ├── 02_toc.jpg
│   └── 03_feature.jpg
└── Elle_2026-05/                ← magazine "Elle", date 2026-05
    ├── p1.png
    └── p2.png
```

**Folder naming convention** (default extractor): `<magazine>_<YYYY-MM-DD>` or `<magazine>_<YYYY-MM>`. Folders that don't match still process — `magazine_name` falls back to the full basename and `issue_date` is null, with a warning. The full basename is always the UNIQUE identity in `publications.name` so multiple issues of the same magazine each get their own row.

**Pluggable extractor.** The parser is one implementation of `PublicationMetadataExtractor` (`src/publication.py`). Same registry pattern as the OCR/layout/NER backends — add a class, register in `PUBLICATION_EXTRACTORS`, switch via `config.yaml.publication_extraction.backend`. The extractor receives the full folder `Path`, so future implementations (sidecar `publication.yaml`, LLM call, ISSN lookup, …) can inspect folder contents and not just the basename. `PublicationInfo.name` and `source_path` are folder-derived and don't depend on the extractor — only `magazine_name` and `issue_date` come from the extractor's output, which keeps the `publications.name` UNIQUE invariant intact across backends.

Each page-image still produces its own JSON output and its own `runs` row in SQLite. The publication grouping is a separate `publications` row that the per-page runs link to via FK, **not** a single multi-page document. This keeps cross-publication queries (e.g. "top brands across all magazines") and per-page artefacts (one JSON per page-image) both natural.

The original folder hierarchy is preserved when files move to `processed/` — `inputs/Vogue_April_2026/01_cover.jpg` → `processed/Vogue_April_2026/01_cover.jpg`. Empty publication folders are removed after their last page is moved; the input root itself is never touched.

**Engineering decisions captured here so future-us doesn't relitigate:**

- **`page_label` is TEXT, not an integer.** Newspaper and magazine pagination is messy: roman numerals for front matter, prefixed labels like `A12` / `B3`. Storing as TEXT means the auto-assigned `"1"`, `"2"`, … can be hand-corrected later without a migration. `runs.id` ASC preserves input order, so we don't need a separate ordinal.
- **Publication identity is the folder basename, UNIQUE on `publications.name`.** Re-running the same folder reuses the row; all runs accumulate against one publication. Two unrelated folders with the same name would collide — rename to disambiguate.
- **Subdirectories of the input root are publications; the input root itself is never one.** Predictable rule that preserves existing flat-batch behaviour for loose files. To process a single publication directly, place its folder inside an input root and pass the parent.
- **`runs.publication_id` is nullable with `ON DELETE SET NULL`.** Loose runs are first-class; deleting a publication keeps its runs (just NULLs the link).
- **`metadata.publication` block in each page's JSON is the same shape stored in the DB.** Each JSON is fully self-describing — no DB lookup required.
- **No `publication.yaml` for richer metadata yet.** The columns (`language`, `notes`) exist as nullable so they can be populated later without migration; we'll add the loader when there's a real need.
- **Forward-compatible migration on first open.** Each schema bump auto-upgrades the DB — `publications` and `runs` columns added via `ALTER TABLE ADD COLUMN`, idempotent and run *before* `executescript(SCHEMA)` because the new schema's indexes reference those columns. Existing rows survive untouched with NULL for the new fields.

## Page classification (editorial vs advertising)

Each page gets a label at JSON-serialization time via `classify_page` in `src/output_handler.py`. The heuristic uses signals already produced by earlier stages:

- **Block-level signal** — the share of text blocks classified as `advertisement_copy` by the layout stage. Crosses into "advertising" at `advertisement_block_ratio` (default 0.5).
- **Image-level signal** — any OWLv2 detection in `advertisement_detection_labels` (default `["advertisement", "product advertisement"]`) at confidence ≥ `advertisement_detection_confidence` (default 0.5).

Either signal alone is enough to flip a page to `advertising`; neither = `editorial`. The decision is written to `pages[].classification` plus a human-readable `classification_reason` ("advertisement_copy ratio 0.62 ≥ 0.50; detection 'advertisement' confidence 0.78"), and the same fields land in the `pages` table.

**Why we picked this shape:**

- **Reuse, not re-classify.** The signals already exist (`block_type` from layout, OWLv2 detections). Wiring them together costs almost nothing.
- **Tunable per project.** All three knobs live in `config.yaml.page_classification`; no code edit needed when a publication needs a different threshold.
- **Future-proofed.** The DB column accepts any string. When a real page-classifier (e.g. CLIP on the page image) lands, it slots in without a schema migration; the heuristic just gets replaced.
- **Explainable.** `classification_reason` says *which* signal fired. Useful for debugging mis-classifications and for downstream filters that want stronger evidence.

## SQLite mirror

`src/output_handler.write_result` writes the JSON file first, then calls `src/db.insert_run` to record the same payload into a SQLite DB (default `database/results.db`). The DB is a queryable mirror of the JSON files, not a replacement.

**Engineering decisions captured here so they survive the next refactor:**

- **JSON is the source of truth, the DB is best-effort.** `insert_run` catches every exception, logs a warning, and returns `None`. A locked DB file or malformed payload can never lose a successful pipeline run. If you ever need to rebuild the DB, replay the JSON files.
- **Normalized over blob.** Eight tables (`publications`, `runs`, `run_errors`, `pages` (incl. classification), `text_blocks`, `entities`, `image_regions`, `detections`) with FK cascades. The reason for having a DB at all is queries like "top brands across all magazines processed with PaddleOCR-VL" — a JSON-blob column would just be a slower filesystem.
- **No `raw_json` column.** Storing the full payload in-row was rejected because table size would explode and add no query value. `runs.output_json_filename` (basename only) plus `output.directory` from config is enough to find the full JSON. Filename-only also means the output and database directories can be moved independently without breaking lookups.
- **One row per run, append-only.** Re-processing the same image with different models is the primary use case (we want to compare backends), so a new `runs` row is inserted every time. The UNIQUE constraint on `output_json_filename` only fires on a true duplicate (same model slug + same timestamp), which is itself a signal something is off.
- **BBoxes as four `REAL` columns.** So spatial filters are indexable, and you don't need JSON1 to ask "which detections sit in the top quarter of a page".
- **Aggregates are not stored.** `document.all_entities` / `document.all_detections_summary` exist in the JSON for human convenience but are recomputed on demand from `entities` / `detections` in SQL, so they can't go stale.

Disable with `database.enabled: false` in `config.yaml` if you want pure-JSON runs.

## Project layout

```
print_document_process_refinement/
├── main.py                       CLI entry point (argparse + Loguru setup)
├── config.yaml                   Default model + prompt configuration
├── pyproject.toml                Project metadata + dependencies (uv)
├── SPEC.md                       Original design spec
├── README.md                     Quick-start usage
├── inputs/                       Drop scans here for batch processing
├── processed/                    Files are moved here after a successful run
├── output/                       JSON results land here
├── logs/                         Loguru rotating log files
└── src/
    ├── pipeline.py               Orchestrator + backend registries
    ├── config.py                 YAML loader, dataclass config, CLI overrides
    ├── input_handler.py          File/folder/publication resolution, PDF → page images
    ├── output_handler.py         JSON serialisation + filename generation + DB hook
    ├── publication.py            Pluggable PublicationMetadataExtractor + registry + factory
    ├── db.py                     SQLite schema (incl. publications) + best-effort insert_run + idempotent migration
    └── models/
        ├── base.py               Dataclasses + abstract interfaces
        ├── ocr/doctr_ocr.py
        ├── ocr/ppstructure.py    Implements both OCRModel + LayoutModel
        ├── layout/layoutlmv3.py  Model path + heuristic fallback
        ├── ner/spacy_ner.py
        └── image_analysis/owlv2.py
```

## Running it

```bash
uv venv && uv pip install -e "."
uv run python -m spacy download en_core_web_trf

uv run python main.py --input path/to/scan.jpg            # single file
uv run python main.py --input ./inputs/                   # batch a folder
uv run python main.py --input scan.pdf -o ./results/      # custom output dir
```

CLI overrides (`--ocr-model`, `--layout-model`, `--ner-model`, `--image-model`, `--log-level`, `--output`) take precedence over `config.yaml`. Supported inputs: `.jpg`, `.jpeg`, `.png`, `.pdf` (each PDF page is rendered at 300 dpi via `pypdfium2` and processed independently).

## Configuration knobs (`config.yaml`)

- `models.<stage>.{backend, model_name, detection, recognition, confidence_threshold}` — pick the backend and weights for each stage.
- `label_remapping` — rewrite spaCy entity labels (defaults to `ORG → BRAND`).
- `detection_prompts` — categorised list of OWLv2 zero-shot prompts; flattened at runtime.
- `output.{directory, include_timestamp, include_model_names}` — controls where results go and how they're named.
- `database.{enabled, path}` — toggle the SQLite mirror and pick its location. JSON output is always written regardless.
- `page_classification.{advertisement_block_ratio, advertisement_detection_confidence, advertisement_detection_labels}` — knobs for the editorial-vs-advertising heuristic. Replaceable by a real classifier without changing the schema.
- `logging.{level, file}` — Loguru level and rotating-file destination (10 MB rotation, 7 days retention; file always captures DEBUG).

## Error handling

- Per-file failures in a batch run are logged and skipped; the next file still runs.
- Per-page failures inside a file are caught, recorded under `errors[]` in the output JSON, and the remaining pages still process.
- Image analysis failures degrade to text-only results rather than aborting the page.
- Missing spaCy weights are downloaded on first load. LayoutLMv3 falls back to its heuristic classifier if the model has no token-classification head.

## Key dependencies

`paddleocr` + `paddlepaddle` (PP-Structure), `python-doctr[torch]`, `transformers` + `torch` + `torchvision` (LayoutLMv3 + OWLv2), `spacy`, `pypdfium2` (PDF rendering), `Pillow`, `opencv-python` (DocTR's region segmentation), `loguru`, `pyyaml`. Python ≥ 3.10. Managed with `uv`.
