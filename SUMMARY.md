# Project Summary — Print Document Intelligence Pipeline

## What this project is

A modular Python pipeline that ingests scanned print media (newspaper/magazine images and PDFs) and produces a structured JSON describing what is on each page: the text that was printed, what kind of text block it is (headline, body, caption, etc.), the named entities mentioned (people, brands, places…), and the objects detected in the photographs/illustrations on the page.

The system is tuned for the **beauty and fashion** publishing domain — its zero-shot vision prompts and entity remappings (e.g. `ORG → BRAND`) reflect that focus.

## What it produces

For each input file the pipeline writes one JSON document to `output/` with this shape:

- `metadata` — input filename, ISO timestamp, models used, pipeline version
- `pages[]` — for each page:
  - `text_blocks[]` — id, type (`headline` / `subheadline` / `body` / `caption` / `byline` / `advertisement_copy` / `other`), recognised text, normalised bbox, extracted entities
  - `image_regions[]` — id, bbox on the page, and OWLv2 detections (label, confidence, bbox inside the crop)
- `document` — aggregated counts: every entity with frequency, every detection label with frequency, total page count
- `errors` — any per-page failures captured during the run

Output filenames follow `<input_stem>_<timestamp>_<model_slug>.json`.

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

`Pipeline.run(input_path)` → resolves files → loads all models once → for each file: render pages → process each page through stages → write JSON → move the original file to a sibling `processed/` directory.

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
    ├── input_handler.py          File/folder resolution, PDF → page images
    ├── output_handler.py         JSON serialisation + filename generation
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
- `logging.{level, file}` — Loguru level and rotating-file destination (10 MB rotation, 7 days retention; file always captures DEBUG).

## Error handling

- Per-file failures in a batch run are logged and skipped; the next file still runs.
- Per-page failures inside a file are caught, recorded under `errors[]` in the output JSON, and the remaining pages still process.
- Image analysis failures degrade to text-only results rather than aborting the page.
- Missing spaCy weights are downloaded on first load. LayoutLMv3 falls back to its heuristic classifier if the model has no token-classification head.

## Key dependencies

`paddleocr` + `paddlepaddle` (PP-Structure), `python-doctr[torch]`, `transformers` + `torch` + `torchvision` (LayoutLMv3 + OWLv2), `spacy`, `pypdfium2` (PDF rendering), `Pillow`, `opencv-python` (DocTR's region segmentation), `loguru`, `pyyaml`. Python ≥ 3.10. Managed with `uv`.
