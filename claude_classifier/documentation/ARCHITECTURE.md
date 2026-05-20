# Architecture

## Overview

`claude_classifier` runs two sequential Claude calls per magazine:

```
Inputs
  ├── inputs/<folder>/*.jpg                       page scans
  ├── ocr_eval/googlevision_output/<folder>/      pre-computed OCR
  └── database/dmr.db                             monitored-brand aliases
                                │
                                ▼
        ┌──────────────────────────────────────────────┐
        │  Pass 1  (per-page, Anthropic Batch API)     │
        │  Sonnet 4.6 · vision + OCR · tool use        │
        │  → output/<run_id>/pass1/<image_id>.json     │
        └──────────────────────────────────────────────┘
                                │
                                ▼
        ┌──────────────────────────────────────────────┐
        │  Reconcile  (in-process, no API)             │
        │  DMR Aho-Corasick over each page's OCR text  │
        │  → canonical brand list per page             │
        └──────────────────────────────────────────────┘
                                │
                                ▼
        ┌──────────────────────────────────────────────┐
        │  Pass 2  (whole magazine, Messages API)      │
        │  Opus 4.7 · summaries + masthead OCR         │
        │  → pass2_runs/<ts>/results/<image_id>.json   │
        └──────────────────────────────────────────────┘
```

Pass 1 is **embarrassingly parallel** (batch API submits all pages in one
request, Anthropic processes them concurrently, 50% discount). Pass 2 is
**inherently sequential** (one prompt that sees every page summary), but
chunks the *output* into ≤200 pages per call so the response stays within
`max_tokens`.

## Pass 1 — per-page analysis

**Input per request** (one `Request` per page in the batch):

- System prompt (cached ephemeral): [`prompts/pass1_system.md`](./prompts/pass1_system.md)
- Tool definition (cached implicitly by the SDK): `PASS1_TOOL` from
  [`schemas.py`](./schemas.py) — required fields, enums, descriptions
- User message:
  1. Page image as a base64 `image` block
  2. Text block: `sequence_index`, `image_id`, GoogleVision OCR fenced as code

**Output** — forced via `tool_choice={"type": "tool", "name": "record_page_analysis"}`,
so the response is guaranteed to be schema-conformant JSON. Written verbatim
to `output/<run_id>/pass1/<image_id>.json`.

**Lifecycle:**

1. `submit(input_path)` discovers pages, builds requests, posts the batch,
   records `batch_id` in `runs.db`, writes `run_metadata.json`, returns
   `run_id`. The Anthropic batch processes asynchronously (typical: minutes;
   SLA: 24h).
2. `collect(run_id)` polls the stored `batch_id`. If still in progress, exits
   non-zero (scriptable). On completion, iterates `batches.results()` and
   writes one JSON per page. Failures produce `{"error": ..., "image_id": ...}`
   placeholders (never aborts the run).

**Cost tracking** — each result carries `message.usage`; per-page
`CostBreakdown` objects are summed and persisted to:
- `runs.db.pass1_batches.{input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens, cost_usd, batch_discount}`
- `run_metadata.json["pass1"]["cost"]`

## Reconcile — DMR alias matching

In-process step between pass 1 and pass 2. No API call.

[`dmr_matcher.py`](./dmr_matcher.py) builds a single Aho-Corasick automaton at
process startup from `database/dmr.db`. Per page, [`reconcile.py`](./reconcile.py)
calls `matcher.match(ocr_text)` and returns deduped `CanonicalBrand(name,
entity_type)` records.

Matcher rules (vendored from the open-source pipeline):

- **Normalisation**: NFKD-strip diacritics → lowercase → collapse internal
  whitespace → strip punctuation except `&`, `+`, `'`, `.`, `/`, `@`.
- **Specificity** when an entity is reachable as multiple types: `BRAND` >
  `COMMERCIAL_COMPANY` > `COMPANY` > `HOLDING`.
- **Tie-break** on equal specificity: lowest numeric `entity_id` (deterministic).
- **Word-boundary filter**: prevents `Mac` inside `Macaron` matching.
- **`min_alias_length` = 3**, default stopword filter on common articles.

**Surfaced output**: in pass 2 every page gets `brands.canonical` written into
its final JSON as `[{"name": ..., "entity_type": "BRAND"}, ...]`. The raw list
is intentionally not filtered — many "brands" in the DMR CSV are common
English words / celebrity first names / product nouns, so consumers should
expect false positives. Filtering (intersection with `claude_visual`,
specificity ≥ COMPANY, multi-word only, etc.) is a downstream concern.

## Pass 2 — cross-page revision

**Single prompt sees every page summary** so cross-page reasoning is
consistent regardless of which chunk is being revised. The chunk only
constrains *which* pages the model emits revisions for.

**Input per call:**

- System prompt (cached): [`prompts/pass2_system.md`](./prompts/pass2_system.md)
  — encodes the DMR flowchart (Step 1 obvious-feature labels → Step 2 pure
  advertising → Step 3 editorial vs. advertorial-by-structure, with
  continuation-page lookback for missing-byline pages).
- Tool: `PASS2_TOOL` (only revises `article_type.final` + `revision_reason` +
  `monography.{present, subject, subtype}`).
- User message — single JSON document with four top-level keys:
  - `publication_context` — `{publication_name, issue_date, country, suffix}`
  - `all_pages` — array of compact pass-1 summaries (one per page in the magazine)
  - `anchor_masthead_ocr` — `{image_id: full_OCR_text}` for masthead pages only
  - `revise_pages` — image_ids in *this* chunk

**Compact summary shape** (per page, in `all_pages`):

```jsonc
{
  "image_id": "42524619",
  "seq": 1,
  "structural_role": "cover",
  "printed_page_number": null,
  "byline": {"editor": null, "photographer": null},
  "brands_dominant": "VOGUE",
  "brands_canonical": ["VOGUE", "OLIVIA", "RODRIGO"],
  "signals": {
    "labels_found": [],
    "has_qr_or_barcode": false,
    "magazine_x_brand_headline": null,
    "contact_info_on_page": false,
    "looks_like_ad": false
  },
  "article_type_initial": "editorial",
  "monography_initial": {"present": false, "subject": null, "subtype": null}
}
```

**Output** — `tool_choice={"type": "any"}` lets Claude emit one
`record_page_revision` tool call per `image_id` in `revise_pages`. The runner
merges revisions into the original pass-1 JSON and writes the result to
`pass2_runs/<ts>/results/<image_id>.json`. Fields not covered by the revision
tool are passed through unchanged from pass 1.

Multiple pass-2 runs are kept on disk; `current_pass2` is a symlink to the
most recent one.

**Cost tracking** — `response.usage` from each chunk is summed and persisted to:
- `runs.db.pass2_runs.{input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens, cost_usd}`
- `run_metadata.json["pass2_runs"][<pass2_run_id>]["cost"]`
- `pass2_runs/<ts>/cost.json` (standalone copy)

## Data flow contracts

### Pass-1 output shape (frozen)

```jsonc
{
  "sequence_index": 1,
  "ocr_text_present": true,
  "structural_role": "cover" | null,
  "printed_page_number": "12" | "iv" | "A3" | null,   // TEXT, not int
  "byline": {"editor": str|null, "photographer": str|null},
  "brands": {"claude_visual": [str], "dominant": str|null},
  "signals": {
    "labels_found": [str],
    "has_qr_or_barcode": bool,
    "magazine_x_brand_headline": str|null,
    "contact_info_on_page": bool,
    "layout": {
      "bleeds_to_edge": bool,
      "single_image_dominates": bool,
      "has_body_copy_columns": bool,
      "looks_like_ad": bool
    }
  },
  "article_type": {
    "initial": "editorial"|"advertising"|"advertorial"|"unknown",
    "confidence": 0.0-1.0,
    "evidence": str,
    "final": ...,             // overwritten by pass 2
    "revision_reason": ...    // overwritten by pass 2
  },
  "celebrity": {"present": bool, "candidates": [str], "evidence": str|null},
  "bridal":    {"present": bool, "evidence": str|null},
  "monography": {"present": bool, "subject": str|null, "subtype": ...|null, "evidence": str|null},
  "notes": str|null
}
```

### Pass-2 additions (merged into pass-1 JSON)

- `article_type.final`, `article_type.confidence`, `article_type.revision_reason`
- `monography.{present, subject, subtype}`
- `brands.canonical` — `[{"name": str, "entity_type": "BRAND"|"COMMERCIAL_COMPANY"|"COMPANY"|"HOLDING"}]`

## Storage layout

```
output/<run_id>/
├── pass1/                       pass-1 JSONs (immutable after collection)
│   └── <image_id>.json
├── pass2_runs/
│   └── <timestamp>/
│       ├── results/<image_id>.json
│       └── cost.json
├── current_pass2 -> pass2_runs/<latest>
└── run_metadata.json
```

- `pass1/` is **append-only after `collect()`**; pass 2 is non-destructive.
- `pass2_runs/<ts>/` is a fresh directory every time so prompt-iteration A/B
  comparison is trivial.
- `current_pass2` is a symlink for downstream consumers that want "latest".

## SQLite tracking (`runs.db`)

JSON files on disk are the source of truth; the DB just mirrors orchestration
state. A DB failure must never abort a pipeline run.

Tables:

| Table | Purpose |
|---|---|
| `pass1_batches` | one row per pass-1 submission (status, batch_id, page_count, cost) |
| `pass1_page_results` | one row per page (status, error, custom_request_id) |
| `pass2_runs` | one row per pass-2 attempt (status, chunk_count, cost) |

Cost columns are added by an idempotent `ALTER TABLE` so old DBs upgrade in
place.

## Backend choices

| Decision | Choice | Why |
|---|---|---|
| Pass 1 model | Sonnet 4.6 | cheapest tier capable of vision + tool use at production volume |
| Pass 1 transport | Batch API | 50% discount; pages are independent |
| Pass 2 model | Opus 4.7 | hardest reasoning task (DMR flowchart + cross-page) |
| Pass 2 transport | Messages API | needs full magazine context in one prompt |
| OCR | GoogleVision (precomputed) | not part of this module; consumed verbatim |
| Brand matching | Aho-Corasick over SQLite | O(text length) per page; deterministic |
| Schema enforcement | Forced tool use | guarantees JSON-conformant responses |
| Caching | `cache_control: ephemeral` on system prompts | both passes amortise prompt cost |

## Failure modes & resilience

| Failure | Behaviour |
|---|---|
| Anthropic batch returns partial errors | Per-page error JSON written; `status=partial`; pass 2 skips error pages |
| OCR file missing for an image | `extract_ocr_text` returns empty string; pass 1 still runs (image-only) |
| `database/dmr.db` missing | Reconcile raises; pass 1 still works without it. Run the import script. |
| SQLite write fails | Logged warning; pipeline continues (JSON is source of truth) |
| Pass-2 response missing tool calls for some pages | Those pages keep pass-1 `initial` as `final`; revision_reason stays null |
| `run_metadata.json` cost write fails | Logged warning; DB still has the cost |

## What's intentionally **not** included

- **Page images in pass 2** — would balloon cost; pass 1 has already extracted
  the visual signals into `signals.*`.
- **Per-page full OCR in pass 2** — only mastheads are sent (used for byline
  verification).
- **Fuzzy DMR matching** — deferred until per-token OCR confidence is wired.
- **Continuation-page byline lookback across runs** — confined to a single
  pass-2 call's `all_pages` payload.
- **OCR ingestion** — that's the `ocr_eval/` module's concern.
