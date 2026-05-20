# Print Document Intelligence Pipeline — Claude Working Guide

## Project overview

Modular Python pipeline that ingests scanned print media (magazine/newspaper images and PDFs) and produces structured JSON per page: OCR text blocks, layout classification, named entity recognition (including DMR brand matching), and zero-shot image analysis. Tuned for the beauty and fashion publishing domain (Launchmetrics / DMR).

## Tech stack

- **Python** (managed via `uv`)
- **PaddleOCR-VL 1.5** — default OCR + layout backend (VLM recognition offloaded to MLX-VLM server on Apple Silicon)
- **spaCy** (`en_core_web_trf`) — NER
- **OWLv2** (`google/owlv2-base-patch16-ensemble`) — zero-shot image analysis (MPS on Apple Silicon)
- **LayoutLMv3** — layout classification (falls back to geometry heuristic if no classification head)
- **DMR alias matcher** — Aho-Corasick lookup against `dmr_monitored_brands.csv` (~221k rows) for BRAND / COMPANY / HOLDING entity labelling
- **SQLite** — best-effort queryable mirror of JSON output (`database/results.db`)
- **direnv** — auto-starts MLX-VLM server on `cd` into project

## Key files

```
main.py                        CLI entry point
config.yaml                    All model/output/DB settings (CLI args override)
src/pipeline.py                Wires backends via registries; Pipeline.run()
src/models/base.py             Abstract base classes + frozen dataclasses (DO NOT CHANGE INTERFACES)
src/models/                    Concrete model implementations
src/input_handler.py           Resolves --input path → flat list of InputItems
src/output_handler.py          Writes JSON; page classification heuristic
src/db.py                      SQLite mirror (best-effort; never fatal)
src/publication.py             Folder-name parser → PublicationInfo
dmr_monitored_brands.csv       Brand/company/holding lookup table (project root)
```

## Architecture

```
Input (JPG/PNG/PDF)
  │
  ▼
[1] OCR + page segmentation     → text blocks + image-region crops
  │                               (PaddleOCR-VL default; ppstructure / doctr alternatives)
  ├──► [2a] Layout classification → block type per text block
  │                                 (paddleocr_vl shares same instance as OCR)
  ├──► [2b] spaCy NER             → PERSON, GPE, LOC, PRODUCT, EVENT, DATE, WORK_OF_ART, ORG
  │
  ├──► [2c] DMR alias matcher     → BRAND / COMPANY / HOLDING with dmr_id chain enrichment
  │                                 (Aho-Corasick; overlapping spaCy spans replaced by alias match)
  └──► [3]  OWLv2 image analysis  → detections per image region (non-fatal; empty on failure)
                   │
                   ▼
              JSON output  →  SQLite mirror (best-effort)
```

**Backend registries** in `src/pipeline.py`:
```python
OCR_BACKENDS     = { "paddleocr_vl": ..., "doctr": ..., "ppstructure": ... }
LAYOUT_BACKENDS  = { "paddleocr_vl": ..., "layoutlmv3": ..., "ppstructure": ... }
NER_BACKENDS     = { "spacy": ..., "dmr_alias_matcher": ... }
IMAGE_ANALYSIS_BACKENDS = { "owlv2": ... }
```
Adding a new backend = implement the interface in `src/models/base.py`, register in the dict.

## Coding rules

- **Never change the abstract interfaces** in `src/models/base.py` (`OCRModel`, `LayoutModel`, `NERModel`, `ImageAnalysisModel`) or the frozen dataclasses (`TextBlock`, `ClassifiedTextBlock`, `Entity`, `ImageRegion`, `Detection`, `PageResult`, `DocumentResult`). All bounding boxes are normalised to `[0, 1]`.
- **New backend = implement interface + register in dict.** No changes to `Pipeline.run()` or callers.
- **JSON is source of truth; DB is best-effort.** `db.insert_run` must catch all exceptions and log a warning — a DB failure must never abort a pipeline run.
- **Do not store aggregates in the DB.** `document.all_entities` / `document.all_detections_summary` are recomputed from `entities` / `detections` tables on demand.
- **`page_label` is TEXT, not integer.** Magazine pagination can be roman numerals or prefixed (`A12`). Do not cast to int.
- **Publication identity = folder basename** (UNIQUE on `publications.name`). Re-running the same folder accumulates runs against one publication row.
- **Stage 3 failure is non-fatal.** OWLv2 exceptions must be caught; log and emit empty detections.
- **DMR alias matcher spans beat spaCy spans on overlap.** Where character offsets overlap, alias matcher wins; spaCy entry is dropped.
- **No `ORG → BRAND` remapping** in `label_remapping` config — `BRAND` is produced only by the alias matcher. `ORG` is preserved for non-monitored organisations.
- **Normalization is symmetric:** apply the same lossless + lossy transforms to CSV at index time and to OCR text at lookup time.

## Commands

### Install
```bash
uv venv && uv pip install -e "."
uv run python -m spacy download en_core_web_trf
```

### Run pipeline
```bash
# Single file
uv run python main.py --input path/to/scan.jpg

# Folder of scans
uv run python main.py --input ./inputs/

# With options
uv run python main.py -i ./inputs/ -o ./results/ --log-level DEBUG
```

### MLX-VLM servers (Apple Silicon — managed via `./scripts/mlx`)
```bash
./scripts/mlx status                # which servers are listening
./scripts/mlx start paddle          # idempotent
./scripts/mlx stop paddle
./scripts/mlx restart paddle        # after model change
./scripts/mlx logs paddle
```

### MPS fallback (if OWLv2 / LayoutLMv3 hit unsupported op)
```bash
PYTORCH_ENABLE_MPS_FALLBACK=1 uv run python main.py -i ./inputs/
```

## Configuration

Edit `config.yaml` — all CLI args override config values. Key sections:

| Section | What it controls |
|---|---|
| `models.ocr.backend` | `paddleocr_vl` (default) / `ppstructure` / `doctr` |
| `models.ner.backend` | `spacy` / `dmr_alias_matcher` |
| `models.image_analysis.confidence_threshold` | OWLv2 detection threshold (default 0.3) |
| `page_classification` | `advertisement_block_ratio` (0.5), detection confidence + labels |
| `database.enabled` | Set `false` for pure-JSON runs |
| `publication_extraction.backend` | `folder_name_regex` (default) |

## Input folder convention

```
inputs/
├── loose_scan.jpg               ← standalone (no publication)
├── Vogue_2026-04-15/            ← publication: files sorted alphabetically → page_label "1", "2", …
│   ├── 01_cover.jpg
│   └── 02_toc.jpg
```
Folder naming: `<magazine_name>_<YYYY-MM-DD>` or `<magazine_name>_<YYYY-MM>`. Mismatches still process — `magazine_name` falls back to full basename, `issue_date` is null.

## Output

- JSON → `output/<input_stem>_<timestamp>_<model_slug>.json`
- Successfully processed inputs moved to `processed/` (folder hierarchy preserved)
- SQLite → `database/results.db` (mirror only; rebuild from JSON if lost)

## DMR alias matcher — key rules

- Built once at startup from `dmr_monitored_brands.csv`; Aho-Corasick for O(text-length) search
- Specificity: `BRAND > COMPANY (incl. COMMERCIAL_COMPANY) > HOLDING`
- Tie-break on ID collision: **lowest numeric ID wins** (deterministic, reproducible)
- Word-boundary filtering prevents substring false positives (`Mac` inside `Macaron`)
- Fuzzy matching for OCR errors is **out of scope** — add later gated on per-token confidence
- Multi-column reading-order reconstruction is a Stage 1 (OCR) concern, not the matcher's
