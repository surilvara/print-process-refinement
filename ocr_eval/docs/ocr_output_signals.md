# OCR Output Signals — Reference

Catalogue of every data point that lives inside a runner's normalised
`OcrOutput` JSON, what each one means, and how useful it is as an
input to a salvage / routing rule (e.g. the `--salvage-rule` flag in
[`hybrid.py`](../hybrid.py)).

Reading this once should answer:

1. **What is actually stored** in `outputs/<runner>/<stem>.json`?
2. **What can I compute from it** without re-opening the source image?
3. **Why would I use each signal** as a routing decision?

The canonical schema is defined in [`schema.py`](../schema.py) (`OcrOutput`,
`OcrBlock`, `ImageRegion`, `BBox`). All bounding boxes are normalised to
`[0, 1]` so every geometry-derived metric is resolution-independent.

---

## What's in the file (schema recap)

```jsonc
{
  "image_stem":   "00000017_42524635",
  "image_width":  3000,
  "image_height": 4000,
  "runner":       "paddleocr_vl",
  "full_text":    "…concatenated text…",
  "blocks": [
    {
      "text":       "…",
      "bbox":       { "x_min": 0.10, "y_min": 0.05, "x_max": 0.45, "y_max": 0.12 },
      "confidence": 0.92,
      "block_type": "headline"    // or "body", "caption", "unknown", …
    }
  ],
  "image_regions": [
    {
      "bbox":        { "x_min": 0.0, "y_min": 0.2, "x_max": 1.0, "y_max": 0.9 },
      "region_type": "photo",
      "confidence":  0.0
    }
  ],
  "source_image_path": "/abs/path/to/scan.jpg"   // optional
}
```

Hybrid outputs additionally carry four audit fields injected by
[`hybrid.py`](../hybrid.py):

```jsonc
{
  "source":           "primary",      // or "fallback"
  "salvage_trigger":  "blocks == 0",  // or null
  "primary_runner":   "paddleocr_vl",
  "fallback_runner":  "glm_ocr"
}
```

---

## Signal tiers

Signals are grouped by how expensive they are to compute and how
runner-portable they are. **Tiers 1–3 work on any conforming
`OcrOutput`.** Tier 4 requires the runner to emit meaningful
`block_type` labels. Tier 5 operates on the raw text string.

### Tier 1 — Counts (cheapest, always available)

| variable | derivation | useful for catching |
|---|---|---|
| `blocks` | `len(output.blocks)` | empty pages or severe under-segmentation |
| `hyp_chars` | `len(output.full_text)` | total text volume |
| `image_regions` | `len(output.image_regions)` | image-heavy pages (ads, photo spreads) |
| `has_text` | `hyp_chars > 0` | binary text-present flag |

**Why useful:** these are the first-pass triage signals. `blocks == 0`
tells you the OCR detected nothing, but **note** (see [hybrid v1
experiment](#known-pitfalls)) that "0 blocks" often means the page is
genuinely empty, not that the OCR failed. Pair with another signal
before triggering a fallback.

---

### Tier 2 — Confidence statistics

PaddleOCR-VL emits a per-block confidence score. Other runners may emit
`0.0` or a non-calibrated value — **always verify what your runner
actually writes** before relying on these.

| variable | derivation |
|---|---|
| `mean_confidence` | mean of `b.confidence for b in blocks` |
| `min_confidence` | weakest block's confidence |
| `max_confidence` | strongest block's confidence |
| `low_conf_blocks` | count of blocks where `confidence < threshold` (e.g. 0.5) |
| `low_conf_ratio` | `low_conf_blocks / blocks` |

**Why useful:** confidence is the OCR engine's own self-assessment.
A page where the engine produced text but reported low confidence on
most of it is a strong fallback candidate — distinct from "produced
nothing" (Tier 1).

**Caveats:**
- Confidence scales are not comparable across runners.
- A model that hallucinates text confidently (e.g. some VLMs) gives
  high `mean_confidence` even when wrong. Confidence is a necessary but
  not sufficient signal.

---

### Tier 3 — Geometry / layout signals

Every block has a normalised bbox; sum/aggregate them to learn about
the layout. These are arguably the most useful signals for routing
because they describe **the page**, not just the OCR's effort on it.

| variable | derivation | catches |
|---|---|---|
| `text_area` | sum of block areas `(xmax-xmin)*(ymax-ymin)` | how much of the page is text |
| `text_area_ratio` | `text_area / 1.0` (page is normalised to 1×1) | sparse vs dense pages |
| `largest_block_area` | max block area | single-logo or single-headline pages |
| `largest_block_ratio` | `largest_block_area / max(text_area, ε)` | dominance of one block (ad-like) |
| `mean_block_area` | `text_area / blocks` | tiny captions vs big body paragraphs |
| `image_region_area` | sum of `image_regions` areas | photo-dominated pages |
| `image_to_text_ratio` | `image_region_area / max(text_area, ε)` | ad/photo spreads |

**Why useful:**
- An advert with one giant logo block has `largest_block_ratio` close
  to 1.0 — distinct from an editorial page with many similarly-sized
  body blocks (`largest_block_ratio` low).
- `text_area_ratio < 0.05 AND image_region_area > 0.3` is a strong
  "photo-dominant ad page" signal regardless of how much text was
  extracted.

---

### Tier 4 — Block-type signals (runner-dependent)

`OcrBlock.block_type` and `ImageRegion.region_type` are optional layout
labels. Default is `"unknown"`. **Only useful if the runner actually
sets meaningful values** — verify before relying on them.

| variable | derivation |
|---|---|
| `block_types` | `set(b.block_type for b in blocks)` |
| `has_body_text` | `'body' in block_types` |
| `headline_count` | count of `block_type == 'headline'` |
| `caption_count` | count of `block_type == 'caption'` |
| `unknown_type_ratio` | `count(unknown) / blocks` |
| `region_types` | `set(r.region_type for r in image_regions)` |

**Why useful:** the cleanest editorial-vs-ad signal you can get
without a separate classifier. `has_body_text == False AND
image_regions >= 1` is essentially "no article text, image present" =
likely advert.

**Verification step before using:**
```bash
python3 -c "
import json, glob
from collections import Counter
c = Counter()
for p in glob.glob('outputs/paddleocr_vl/*.json'):
    for b in json.load(open(p))['blocks']:
        c[b.get('block_type','unknown')] += 1
print(c.most_common())
"
```
If the distribution is `{"unknown": 99999}`, Tier 4 is not yet
available for that runner.

---

### Tier 5 — Text-pattern signals (lossy, language-specific)

Statistics computed directly from `full_text`. Easiest to spoof, most
language- and domain-dependent — use as **tie-breakers**, not primary
triggers.

| variable | derivation | rough interpretation |
|---|---|---|
| `digit_ratio` | `sum(c.isdigit())/len(text)` | high on TOC, price tags, mastheads |
| `upper_ratio` | `sum(c.isupper())/len(text)` | high on logo/headline-only pages |
| `whitespace_ratio` | `sum(c.isspace())/len(text)` | tokenisation hint |
| `word_count` | `len(text.split())` | redundant with hyp_chars but easier to read |
| `mean_word_len` | `chars / word_count` | gibberish OCR tends to extreme word lengths |
| `unique_word_ratio` | `len(set(words)) / word_count` | repetitive output detector |

**Why useful:** these catch *quality* failures even when text was
extracted — e.g. a model that returns the same word 30 times has
`unique_word_ratio` near zero. They're cheap and additive to the other
tiers.

---

## Combined-signal rule recipes

Examples of how you'd combine signals into a meaningful salvage rule.
Each can be passed to `hybrid.py --salvage-rule "<expr>"`.

| intent | rule |
|---|---|
| Catch true paddle failures, not "correctly empty" pages | `blocks == 0 and image_regions > 0` |
| Salvage logo-only ad pages | `largest_block_ratio > 0.8 and hyp_chars < 50` |
| Salvage pages where the OCR is uncertain | `mean_confidence < 0.5 and hyp_chars > 0` |
| Salvage photo-dominant pages with sparse text | `text_area_ratio < 0.05 and image_region_area > 0.3` |
| Salvage suspected hallucination (repetitive output) | `word_count > 50 and unique_word_ratio < 0.2` |
| Salvage anything where paddle clearly under-segmented | `blocks <= 1 and image_region_area > 0.5` |

---

## Known pitfalls

### `blocks == 0` is a misleading proxy for "OCR failed"

Empirically observed on Vogue UK April 2026 (255 pages):

- 28 pages had `paddleocr_vl` blocks == 0.
- On those 28 pages, paddle CER averaged **0.54** (mostly 0.0 — the page
  was genuinely near-empty, GV also returned ~6 chars total).
- Switching to glm_ocr on those pages produced CER **1.72** because
  glm hallucinated text where there was none.

Lesson: an empty primary output is not the same as a failed primary
output. Pair Tier 1 emptiness signals with Tier 3 image-region signals
or an external "page-has-text" detector before triggering fallback.

### Confidence is runner-relative

`mean_confidence < 0.5` may be a sensible threshold for paddleocr_vl
but meaningless for a runner that always reports `0.0` or always
reports `1.0`. Audit each runner's confidence distribution before
shipping a confidence-based rule.

### `block_type` is mostly `"unknown"` today

The current PaddleOCR-VL runner doesn't run the layout classifier
head. Tier 4 signals are theoretical until that's wired up.

---

## Recommended exposure tiers in `hybrid.py`

| tier | recommendation |
|---|---|
| 1 (counts) | always expose |
| 2 (confidence) | expose, document caveat |
| 3 (geometry) | expose — highest signal-to-noise for routing |
| 4 (block_type) | opt-in once runners emit real labels |
| 5 (text patterns) | opt-in, document fragility |

Currently `hybrid.py` exposes a subset of Tier 1 + `mean_confidence`
from Tier 2. Extending to Tiers 1–3 is the next sensible step.
