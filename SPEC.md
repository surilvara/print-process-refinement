# Print Document Intelligence Pipeline — Specification

## Overview

A modular Python pipeline that processes scanned newspaper/magazine images to extract structured information across three layers: text extraction, text reasoning/analysis, and image analysis. Designed for the **beauty and fashion** domain.

## Architecture

```
Input (JPEG/PNG/PDF)
        │
        ▼
┌─────────────────┐
│  1. OCR Layer    │  DocTR — text detection + recognition
│                  │  Also: page segmentation (image vs text regions)
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────────┐
│ Text   │ │ Image regions │
│ blocks │ │ (crops)       │
└───┬────┘ └──────┬───────┘
    │              │
    ▼              ▼
┌────────────┐ ┌───────────────┐
│ 2. Text    │ │ 3. Image      │
│ Reasoning  │ │ Analysis      │
│            │ │               │
│ LayoutLMv3 │ │ OWLv2         │
│ spaCy NER  │ │ (zero-shot)   │
└─────┬──────┘ └──────┬────────┘
      │                │
      ▼                ▼
┌──────────────────────────┐
│   JSON Output            │
│   output/<timestamp>_    │
│   <models>.json          │
└──────────────────────────┘
```

Each pipeline stage is behind a **clean abstract interface** so models can be swapped without changing the rest of the pipeline.

---

## Pipeline Stages

### Stage 1: OCR + Page Segmentation (DocTR)

- **Model**: DocTR (`db_resnet50` detection + `crnn_vgg16_bn` recognition, or configurable)
- **Input**: A single page image (numpy array / PIL Image)
- **Output**:
  - List of text blocks with content and bounding boxes
  - List of image regions (non-text areas) as cropped images with bounding boxes
- **Responsibilities**:
  - Detect and recognise all text in the scan
  - Segment the page into text regions vs image regions
  - Return both with spatial coordinates (normalised bounding boxes)

### Stage 2: Text Reasoning + NER

#### 2a. Layout Classification (LayoutLMv3)

- **Model**: LayoutLMv3 (Hugging Face `microsoft/layoutlmv3-base` or fine-tuned variant)
- **Input**: Text blocks with bounding boxes + page image
- **Output**: Each text block classified as one of:
  - `headline`
  - `subheadline`
  - `body`
  - `caption`
  - `byline`
  - `advertisement_copy`
  - `other`
- **Notes**: LayoutLMv3 takes text, bounding boxes, and image patches as joint input — leverages all three modalities.

#### 2b. Named Entity Recognition (spaCy)

- **Model**: spaCy (e.g., `en_core_web_trf` or configurable)
- **Input**: Classified text blocks
- **Output**: Entities extracted per text block:
  - `PERSON` — people mentioned
  - `ORG` — organisations, brand names
  - `EVENT` — event names
  - `GPE` / `LOC` — locations
  - `PRODUCT` — product names
  - `DATE` — dates mentioned
  - `WORK_OF_ART` — publication names, titles
- **Notes**: Standard spaCy entity types for v1. Can be extended with custom entity patterns or replaced with a transformer NER model later. **Brand/company/holding labelling is delegated to the DMR alias matcher (2c) below**; spaCy provides the non-DMR labels (`PERSON`, `GPE`, `LOC`, `PRODUCT`, `EVENT`, `WORK_OF_ART`, `DATE`).

#### 2c. Brand / Company / Holding Matching (DMR alias dictionary)

Replaces the previous blunt `ORG → BRAND` remap with a deterministic dictionary lookup against the list of entities Launchmetrics actually monitors. Mirrors Stage 2 of the existing DMR OCR pipeline (Alberto + Massimiliano's custom alias matcher — session 6).

- **Source**: `dmr_monitored_brands.csv` at the project root. ~221k rows.
  - Columns: `HOLDING_ID`, `HOLDING`, `COMPANY_ID`, `COMPANY`, `COMMERCIAL_COMPANY_ID`, `COMMERCIAL_COMPANY`, `BRAND_ID`, `BRAND`.
  - The CSV has four name levels; the output schema has three labels. **`COMMERCIAL_COMPANY` (the *Marchio Commercializzato* — the distributor entity) is folded into `COMPANY` for labelling purposes.**

- **Labelling rule**. For each OCR-matched value, look up which columns it appears in across the entire CSV (not row-bound). Assign the label of the **most specific column** in which it appears anywhere. Specificity:

  ```
  BRAND  >  COMPANY (incl. COMMERCIAL_COMPANY)  >  HOLDING
  ```

  Worked examples:
  - "Gucci" — appears in any row's `BRAND` column → **`BRAND`** (even though it also appears in `COMPANY` and `HOLDING` rows).
  - "Kering" — appears in `HOLDING` and `COMPANY` columns but never in `BRAND` → **`COMPANY`**.
  - A name appearing only in `HOLDING` → **`HOLDING`**.

- **Normalization**. Applied **symmetrically** to CSV aliases at index time and OCR text at lookup time. Asymmetric normalization is what breaks matching; consistent normalization only expands recall.
  - **Lossless** (no information lost that distinguishes entities): trim + collapse internal whitespace; uppercase; Unicode NFKC; fold smart quotes/backticks to `'`; fold accents (`é → E`).
  - **Lossy** (deliberate collapse): strip legal-form suffixes — `SRL`, `SPA`, `SAS`, `SNC`, `GMBH`, `LTD`, `LLC`, `INC`, `CO`, `CORP`, `GROUP` (with optional dots).
  - Empirical impact on the current CSV: ~400–550 collision keys per column, mostly duplicate registrations of the same entity (`BI.CI` ≡ `BI.CI SRL`, `OMER` ≡ `OMER SPA`). Acceptable because printed pages almost never carry the legal suffix.

- **Algorithm**. Three phases:
  1. **Build (once at pipeline startup).** Iterate the CSV. For every distinct name across all four columns, pre-resolve its label by the specificity rule (most specific column it appears in *anywhere* in the file) and store the corresponding `BRAND_ID` / `COMPANY_ID` / `HOLDING_ID` at that level. Add **both lossless and lossy normalized forms** to the dictionary, both keyed to the same `(label, dmr_id)` — storing both forms removes the need to back-map offsets after suffix-stripping at lookup time. Build an Aho-Corasick automaton over the normalized keys for O(text-length) multi-pattern search regardless of dictionary size.
  2. **Lookup (per text block).** Normalize the block's text *losslessly*, keeping a `char_map` from normalized-position to original-position so matches can be translated back to the original string. Run AC. Filter results to **word-boundary** matches (start at position 0 or after a non-word char; end at len or before a non-word char) — this is what stops `Mac` matching inside `Macaron` while still allowing `Saint Laurent` to match across a space. Map surviving match offsets back through `char_map` to produce original-text spans.
  3. **Merge (per text block).** Combine alias-matcher entities with spaCy entities per the Composition rule below.

- **Output**. Extends the existing `entities[]` array on each text block (additive — no schema break for existing fields). Each alias-matcher hit emits an entity with:
  - `text` — the matched span as it appears on the page (lossless original, not the normalized form)
  - `label` — `BRAND` / `COMPANY` / `HOLDING`
  - `start`, `end` — character offsets within the parent block, consistent with existing entity schema
  - `dmr_id` — the ID from the CSV (`BRAND_ID`, `COMPANY_ID`, or `HOLDING_ID`) at the matched specificity level
  - `dmr_company_id` *(only on `BRAND` matches)* — the `COMPANY_ID` from the same CSV row (or `COMMERCIAL_COMPANY_ID` if folded in)
  - `dmr_holding_id` *(only on `BRAND` and `COMPANY` matches)* — the `HOLDING_ID` from the same CSV row

  Chain enrichment is **upward only** — a brand has one parent company and one parent holding (well-defined per row), but a holding has many companies and a company has many brands (no well-defined downward chain). Matches at `HOLDING` level emit only `dmr_id`. Saves every downstream consumer (Web Digital pre-annotation, advertorial routing, LVMH-score routing) a CSV join.

- **Determinism tie-break — "lowest ID wins"**. Two collision modes are resolved by the **same deterministic rule**: pick the smallest numeric ID at the matched level.
  - **Within-level ID collision**: same normalized name resolves to multiple IDs at the resolved level (e.g., `ADAMANTIS EUROPE` → `BRAND_ID` 10,083,588 *and* 10,083,589 — typically duplicate registrations). Affects ~0.29% of distinct names in the current CSV; HOLDING has zero collisions. Pick the lowest `BRAND_ID` / `COMPANY_ID` / `HOLDING_ID`.
  - **Chain ambiguity**: a `BRAND` name appears in multiple rows with different `(COMPANY_ID, HOLDING_ID)` chains (~0.23% of brand names), or a `COMPANY` name appears under multiple holdings (~1.59% of company names; outliers like `DE RIGO VISION` → 3 holdings). For chain enrichment, pick the row that contains the chosen `dmr_id`; if more than one row matches, pick the one with the smallest `HOLDING_ID`, then smallest `COMPANY_ID`.
  - Rationale: deterministic, reproducible across runs, ~5 lines to implement, and the loss is bounded — most colliding cases are duplicate-data noise (sequential IDs from the same registration). Revisit only if real downstream harm shows up; emitting an array of candidates was rejected because it forces every consumer to handle a list for a 0.3% case.

- **Composition with spaCy NER (2b)**. Both backends run independently on every text block; results are merged at the block level:
  - Where alias-matcher and spaCy entity spans **overlap at the character level**, the alias matcher wins. The overlapping spaCy entry is dropped.
  - Non-overlapping spaCy entities (`PERSON`, `LOC`, `GPE`, `WORK_OF_ART`, `PRODUCT`, `EVENT`, `DATE`, plus `ORG` for non-monitored organisations like "Vatican" or "Harvard") survive unchanged.
  - The previous `ORG → BRAND` entry in `label_remapping` is **removed**. `BRAND` is only ever produced by the alias matcher; spaCy's `ORG` is preserved as `ORG`.

  Worked example. OCR text: `"Kering's house Gucci showed at Milan; bag at Sephora"`. After merge: `Kering` = `COMPANY` (alias), `Gucci` = `BRAND` (alias), `Sephora` = `BRAND` (alias), `Milan` = `GPE` (spaCy). spaCy's three `ORG` hits on `Kering`, `Gucci`, `Sephora` are dropped because each overlaps an alias hit.

- **Configuration** (additive to `config.yaml`):
  ```yaml
  models:
    ner:
      backend: "dmr_alias_matcher"
      csv_path: "dmr_monitored_brands.csv"
      strip_legal_suffixes: true
      fold_accents: true
  ```
  The existing `spacy` backend remains registered for non-DMR labels and runs alongside the alias matcher; spans are merged at the block level per the Composition rule above.

- **Out of scope for this revision** (each is a separate, larger workstream):
  - **Fuzzy / approximate matching** for OCR character errors (e.g. `Hermbs` → `Hermès`). Add later, gated on per-OCR-token confidence. Belongs alongside the matcher, not inside it.
  - **Multi-column reading-order reconstruction** — the `Saint Laurent` split-across-columns case Alberto identified as the dominant Stage 2 failure mode (session 6). Belongs in Stage 1 (OCR), not in the alias matcher.
  - **Cross-page caption-to-product pairing** — the Mail Quotidiana caption-vs-product placement rule (session 4, Francesca's #1 AI blocker). Needs a new pipeline stage; not solvable within NER.

### Stage 3: Image Analysis (OWLv2)

- **Model**: OWLv2 (`google/owlv2-base-patch16-ensemble` or configurable)
- **Input**: Cropped image regions from Stage 1
- **Text prompts** (configurable via config file):
  - People: `"person"`, `"face"`, `"model"`
  - Logos: `"brand logo"`, `"logo"`
  - Fashion/Beauty products: `"clothing"`, `"accessories"`, `"perfume"`, `"makeup"`, `"watch"`, `"jewellery"`, `"handbag"`, `"shoes"`
  - Advertising: `"advertisement"`, `"product advertisement"`
- **Output**: List of detections per image region:
  - Label (matched prompt)
  - Confidence score
  - Bounding box (relative to the crop, and mapped back to full page coordinates)
- **Notes**: Celebrity/person identification skipped for v1 — flagged as future enhancement.

---

## Input Handling

### Supported Formats

| Format | Handling |
|--------|----------|
| JPEG | Load directly as image |
| PNG | Load directly as image |
| PDF | Convert each page to image (e.g., via `pdf2image` / `pypdfium2`) |

### Input Modes

- **Single file**: `python main.py --input scan.jpg`
- **Folder of loose files**: `python main.py --input ./scans/` — each top-level file processed standalone.
- **Folder of publications**: subdirectories of the input root are treated as publications. Files inside each subdirectory are the **pages** of that publication, sorted alphabetically by filename and assigned `page_label` `"1"`, `"2"`, … in input order. Top-level loose files in the same input root remain standalone.
- Mixed formats within a folder are supported.

### Folder-as-Publication

```
inputs/
├── loose_scan.jpg               ← standalone (no publication)
├── Vogue_2026-04-15/            ← publication: 3 pages, magazine "Vogue", date 2026-04-15
│   ├── 01_cover.jpg
│   ├── 02_toc.jpg
│   └── 03_feature.jpg
└── Elle_2026-05/                ← publication: 2 pages, magazine "Elle", date 2026-05
    ├── p1.png
    └── p2.png
```

**Folder naming convention** (default extractor): `<magazine>_<YYYY-MM-DD>` or `<magazine>_<YYYY-MM>`. The basename is parsed at ingestion into `magazine_name` and `issue_date`. The magazine name may itself contain underscores (e.g. `Vogue_Italia_2026-04-15` → magazine `Vogue_Italia`, date `2026-04-15`). Folders that don't match either pattern still process — magazine_name falls back to the full basename, issue_date is null, and a warning is logged. The full basename is always preserved as `publications.name` (the UNIQUE identity key) so multiple issues of the same magazine each get their own row.

**Pluggable extraction.** The folder-name parsing is just one strategy behind a pluggable interface (`PublicationMetadataExtractor` in `src/publication.py`). Alternative implementations (sidecar `publication.yaml`, LLM-driven extractor, ISSN database lookup) register in the `PUBLICATION_EXTRACTORS` dict and switch on via:

```yaml
publication_extraction:
  backend: "folder_name_regex"   # built-in; add your own and reference here
```

The extractor receives the full folder `Path` so implementations can inspect contents, not just the basename. `PublicationInfo`'s identity fields (`name`, `source_path`) are unchanged regardless of extractor, so the `publications.name` UNIQUE invariant holds across backends.

Each page-image still produces its own JSON file and its own `runs` row in SQLite — pages are linked into a publication via the `publications` table, not collapsed into one document. Re-running the same publication folder reuses the existing `publications` row (identity is the folder name); a fresh `runs` row is appended per page per run.

To process a single publication directly, place its folder inside an input root and pass the parent: `--input ./inputs/`. Passing a publication folder *itself* as `--input` will treat its files as standalone (subdirectories of the input root are publications; the input root itself is never a publication).

### Page Classification (editorial vs advertising)

Each page is labelled `editorial` or `advertising` at JSON-serialization time using a heuristic on signals already produced by earlier stages. A page is `advertising` if either:

1. The share of text blocks of type `advertisement_copy` (from layout) meets the configured ratio threshold, **or**
2. Any image-region detection (from OWLv2) with a label in the configured set meets the configured confidence threshold.

Otherwise it is `editorial`. The decision and a human-readable reason ("which signal fired") are written to `pages[].classification` and `pages[].classification_reason` in the JSON, and to the `pages.classification` / `pages.classification_reason` columns in the DB. Tunable via `config.yaml`:

```yaml
page_classification:
  advertisement_block_ratio: 0.5
  advertisement_detection_confidence: 0.5
  advertisement_detection_labels:
    - "advertisement"
    - "product advertisement"
```

The column accepts any string, so a future dedicated page-classifier (e.g. a CLIP-based image classifier) can replace the heuristic without a schema migration.

### PDF Multi-Page Handling

- Each page is processed independently through the full pipeline.
- Output JSON contains:
  - `pages[]` — per-page results
  - `document` — aggregated document-level summary (combined entities, all detections)

---

## Output

### Output Folder

All results written to a configurable output directory (default: `output/`).

### File Naming Convention

```
<input_stem>_<ISO-timestamp>_<ocr-model>_<layout-model>_<ner-model>_<image-model>.json
```

Example:
```
magazine_scan_2026-04-23T14-30-00_doctr_layoutlmv3_spacy_owlv2.json
```

For batch runs, one output file per input file.

### SQLite Mirror

After the JSON file is written, the same payload is also recorded into a SQLite database (default `database/results.db`) so results are queryable across runs. The JSON file remains the source of truth; the DB is a best-effort mirror.

**Engineering decisions:**

- **JSON-first.** The JSON write is unconditional. The DB insert runs after, and any failure (locked file, disk full, malformed payload) is caught, logged as a warning, and swallowed — the pipeline never fails because of the DB.
- **Normalized, not blob.** A six-table schema (below) instead of one row with a JSON column. The whole point of the DB is being able to ask "top brands across all magazines run with model X" without scanning the filesystem.
- **No raw payload column.** Storing the full JSON in the DB doubles the size for no query benefit. Each `runs` row stores `output_json_filename` (basename only) — compose with `output.directory` for the full payload.
- **Append per run.** Re-processing the same input creates a new `runs` row. Comparing model versions on the same input is the primary query case, so we never overwrite. The UNIQUE constraint on `output_json_filename` only kicks in if the same file is replayed (e.g. backfill).
- **Cascade deletes.** All child tables use `ON DELETE CASCADE` so deleting a `runs` row cleans up everything beneath it in one statement.
- **BBoxes as columns, not JSON.** Four `REAL` columns per bbox so spatial filters (`WHERE bbox_y_min < 0.1` for headlines at top of page) are indexable.

**Schema:**

| Table | Key columns |
|---|---|
| `publications` | `id`, `name` (UNIQUE — folder basename), `magazine_name`, `source_path`, `issue_date`, `language`, `notes`, `created_at` |
| `runs` | `id`, `input_file`, `processed_at`, `pipeline_version`, `ocr_model`, `layout_model`, `ner_model`, `image_analysis_model`, `total_pages`, `output_json_filename` (UNIQUE), `publication_id` (FK → publications, ON DELETE SET NULL), `page_label` (TEXT) |
| `run_errors` | `run_id` FK, `page_number` (parsed from "Page N: ..."), `message` |
| `pages` | `run_id` FK, `page_number`, `classification` ('editorial' / 'advertising' — accepts any string), `classification_reason`; UNIQUE(`run_id`, `page_number`) |
| `text_blocks` | `page_id` FK, `block_id` (`tb_000`), `block_type`, `text`, four bbox columns |
| `entities` | `text_block_id` FK, `text`, `label`, `start_offset`, `end_offset` |
| `image_regions` | `page_id` FK, `region_id` (`ir_001`), four bbox columns |
| `detections` | `image_region_id` FK, `label`, `confidence`, four bbox columns (CROP-relative, matching JSON) |

Aggregations in `document.all_entities` and `document.all_detections_summary` are **not stored** — they are recomputable via `GROUP BY` and would only go stale.

**Publication-level decisions:**

- **`page_label` is TEXT, not INTEGER.** Newspaper and magazine page numbering is not always a clean 1..N sequence (Roman numerals for front matter, prefixed labels like "A12" / "B3"). Storing as TEXT avoids a future schema migration when the auto-assigned `"1"`, `"2"`, … gets corrected. Insertion order is preserved by `runs.id` ASC, so we don't need a separate ordinal column.
- **Publication identity = folder name (`publications.name` UNIQUE).** Re-running the same publication folder reuses the existing row so all per-page runs accumulate against one publication. Caveat: two different publications with the same folder name will collide; rename to disambiguate.
- **`runs.publication_id` is nullable, FK ON DELETE SET NULL.** Loose files in the input root remain valid runs with no publication. Deleting a publication won't cascade-delete its runs (we keep the data; the link just becomes NULL).
- **`metadata.publication` block in the JSON** is the same shape stored in the DB, so a single JSON file is fully self-describing without consulting the DB.
- **Forward-compatible migration.** A DB created by the previous (publication-less) version of `db.py` is auto-upgraded on first call: `publications` is created and `runs` gets the two new columns via `ALTER TABLE ADD COLUMN`. Existing rows survive with `NULL` publication info.

### JSON Schema

```json
{
  "metadata": {
    "input_file": "magazine_scan.pdf",
    "timestamp": "2026-04-23T14:30:00Z",
    "models": {
      "ocr": "doctr:db_resnet50+crnn_vgg16_bn",
      "layout": "microsoft/layoutlmv3-base",
      "ner": "spacy:en_core_web_trf",
      "image_analysis": "google/owlv2-base-patch16-ensemble"
    },
    "pipeline_version": "1.0.0",
    "publication": {
      "name": "Vogue_2026-04-15",
      "magazine_name": "Vogue",
      "issue_date": "2026-04-15",
      "source_path": "/abs/path/to/inputs/Vogue_2026-04-15",
      "page_label": "3",
      "total_pages": 12
    }
  },
  "pages": [
    {
      "page_number": 1,
      "classification": "editorial",
      "classification_reason": "advertisement_copy ratio 0.10 < 0.50, no qualifying detections",
      "text_blocks": [
        {
          "id": "tb_001",
          "type": "headline",
          "text": "Summer Fashion Trends 2026",
          "bbox": [0.05, 0.02, 0.95, 0.10],
          "entities": [
            {"text": "Summer Fashion Trends 2026", "label": "EVENT", "start": 0, "end": 26}
          ]
        }
      ],
      "image_regions": [
        {
          "id": "ir_001",
          "bbox": [0.1, 0.15, 0.9, 0.65],
          "detections": [
            {"label": "person", "confidence": 0.92, "bbox": [0.2, 0.2, 0.5, 0.9]},
            {"label": "handbag", "confidence": 0.87, "bbox": [0.6, 0.4, 0.8, 0.7]},
            {"label": "brand logo", "confidence": 0.78, "bbox": [0.85, 0.05, 0.95, 0.12]}
          ]
        }
      ]
    }
  ],
  "document": {
    "all_entities": [
      {"text": "Summer Fashion Trends 2026", "label": "EVENT", "count": 1}
    ],
    "all_detections_summary": {
      "person": 3,
      "brand logo": 2,
      "handbag": 1
    },
    "total_pages": 1
  }
}
```

---

## Configuration

### Config File (`config.yaml`)

```yaml
# Pipeline model configuration — swap models by changing values here
models:
  ocr:
    backend: "doctr"
    detection: "db_resnet50"
    recognition: "crnn_vgg16_bn"
  layout:
    backend: "layoutlmv3"
    model_name: "microsoft/layoutlmv3-base"
  ner:
    backend: "spacy"
    model_name: "en_core_web_trf"
  image_analysis:
    backend: "owlv2"
    model_name: "google/owlv2-base-patch16-ensemble"
    confidence_threshold: 0.3

# OWLv2 detection prompts — add/remove as needed
detection_prompts:
  people:
    - "person"
    - "face"
    - "model"
  logos:
    - "brand logo"
    - "logo"
  fashion_beauty:
    - "clothing"
    - "accessories"
    - "perfume"
    - "makeup"
    - "watch"
    - "jewellery"
    - "handbag"
    - "shoes"
  advertising:
    - "advertisement"
    - "product advertisement"

# Output settings
output:
  directory: "output"
  include_timestamp: true
  include_model_names: true

# Logging
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  file: "logs/pipeline.log"

# SQLite mirror of output JSON. JSON files in output.directory remain the
# source of truth; the DB is best-effort — failures log a warning and the
# pipeline continues. Look up full payload via output_json_filename.
database:
  enabled: true
  path: "database/results.db"
```

### CLI Arguments

```
python main.py --input <file_or_folder> [options]

Options:
  --input, -i        Path to image file or folder (required)
  --output, -o       Output directory (overrides config)
  --config, -c       Path to config file (default: config.yaml)
  --log-level        Logging verbosity (overrides config)
  --ocr-model        Override OCR backend
  --layout-model     Override layout model
  --ner-model        Override NER model
  --image-model      Override image analysis model
```

CLI arguments take precedence over config file values.

---

## Project Structure

```
print_document_process_refinement/
├── main.py                     # CLI entry point
├── config.yaml                 # Default pipeline configuration
├── pyproject.toml              # Project metadata + dependencies (uv)
├── src/
│   ├── __init__.py
│   ├── pipeline.py             # Orchestrator — runs stages in sequence
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract base classes for each stage
│   │   ├── ocr/
│   │   │   ├── __init__.py
│   │   │   └── doctr_ocr.py    # DocTR implementation
│   │   ├── layout/
│   │   │   ├── __init__.py
│   │   │   └── layoutlmv3.py   # LayoutLMv3 implementation
│   │   ├── ner/
│   │   │   ├── __init__.py
│   │   │   └── spacy_ner.py    # spaCy NER implementation
│   │   └── image_analysis/
│   │       ├── __init__.py
│   │       └── owlv2.py        # OWLv2 implementation
│   ├── input_handler.py        # File/folder loading, PDF page extraction
│   ├── output_handler.py       # JSON serialisation, naming, file writing, DB hook
│   ├── publication.py          # Pluggable extractors for (magazine_name, issue_date)
│   ├── db.py                   # SQLite schema + best-effort run insert
│   └── config.py               # Config loading + CLI merge logic
├── output/                     # Generated results (gitignored)
├── logs/                       # Log files (gitignored)
└── tests/
    └── ...
```

---

## Modular Interface Design

Each pipeline stage implements a base interface so models can be swapped:

```python
# src/models/base.py

class OCRModel(ABC):
    @abstractmethod
    def extract(self, image) -> OCRResult:
        """Returns text blocks + image regions with bboxes."""

class LayoutModel(ABC):
    @abstractmethod
    def classify(self, text_blocks, image) -> list[ClassifiedTextBlock]:
        """Classifies text blocks by type (headline, body, etc.)."""

class NERModel(ABC):
    @abstractmethod
    def extract_entities(self, text_blocks) -> list[TextBlockWithEntities]:
        """Extracts named entities from text blocks."""

class ImageAnalysisModel(ABC):
    @abstractmethod
    def detect(self, image_regions, prompts) -> list[ImageDetectionResult]:
        """Detects objects in image regions using provided prompts."""
```

To add a new model: implement the interface, register it in the config, done.

---

## Dependencies

Managed with `uv`. Key packages:

| Package | Purpose |
|---------|---------|
| `python-doctr[torch]` | OCR + page segmentation |
| `transformers` | LayoutLMv3, OWLv2 |
| `torch` | Model inference backend |
| `spacy` | Named entity recognition |
| `Pillow` | Image loading/manipulation |
| `pypdfium2` | PDF to image conversion |
| `loguru` | Logging |
| `pyyaml` | Config file parsing |

---

## Error Handling

- **Batch processing**: If a single file fails, log the error with full traceback via Loguru and continue to the next file.
- **Model loading failures**: Fail fast with a clear error message (missing model, incompatible version).
- **Unsupported file types**: Log a warning and skip.
- **Empty results**: If OCR finds no text or no image regions, still produce an output JSON with empty arrays.

---

## Future Enhancements (Out of Scope for v1)

- **Celebrity/face identification** — face embeddings + reference database lookup
- **Second-stage logo classifier** — crop detected logos → CLIP or logo-specific model for brand identification
- **Image pre-processing** — deskewing, denoising, contrast enhancement
- **LLM-based NER pass** — second pass for domain-specific or ambiguous entities
- **Web API / service mode** — FastAPI wrapper
- **Confidence thresholds per category** — different thresholds for people vs logos vs products
- **Training/fine-tuning pipeline** — fine-tune LayoutLMv3 on beauty/fashion publication layouts
