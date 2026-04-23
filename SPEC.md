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
- **Notes**: Standard spaCy entity types for v1. Can be extended with custom entity patterns or replaced with a transformer NER model later.

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
- **Folder**: `python main.py --input ./scans/` — processes all supported files in the folder
- Mixed formats within a folder are supported.

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
<ISO-timestamp>_<ocr-model>_<layout-model>_<ner-model>_<image-model>.json
```

Example:
```
2026-04-23T14-30-00_doctr_layoutlmv3_spacy_owlv2.json
```

For batch runs, one output file per input file.

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
    "pipeline_version": "1.0.0"
  },
  "pages": [
    {
      "page_number": 1,
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
│   ├── output_handler.py       # JSON serialisation, naming, file writing
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
