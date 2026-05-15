# Print Data Entry (DMR) — Process Analysis

**Source:** Alberto Tornielli (DMR engineering), Suril Vara (engineering), Mariana Martella — 5 May 2026 (transcript timestamp 12:02–12:31)
**Focus:** OCR pipeline architecture, Google Vision API integration, brand identification matching engine, open-source OCR evaluation, LLM-assisted improvements

> **Transcription note resolved by this session:** Earlier session auto-transcripts (notably Session 4) rendered **"OCR"** (English pronunciation "oh-see-arr") as **"SIAR"** throughout. There is no system called SIAR — it was a recurring mistranscription. This session's clean transcript with engineering (Alberto) confirms the canonical name **"OCR pipeline"**. The queue table is `OCR_Image_Queue`.

---

## 1. End-to-End Workflow (Actions)

This session covers the technical pipeline that runs **upstream of operator data entry**, not the operator workflow itself. The pipeline runs automatically as new images enter the system.

### Stage 0 — Image ingestion (Print Image Management)
1. Digitalization team receives PDFs via FTP, email, or downloads them through publisher-supplied software.
2. Team uploads new magazines into the **Print Image Management** application — an internal tool that converts PDFs / physical scans into image assets at the correct resolutions.
3. Images are written to an **S3 bucket** with a date-tree structure (`year/month/...`), in two formats: high-resolution master (used by client platforms) and thumbnails (used in galleries/previews).
4. Each new image is registered in the database table **`OCR_Image_Queue`** (accessible from Web Digital and Databricks).

### Stage 1 — OCR text extraction (Google Vision API)
5. The pipeline picks up new images from the queue table.
6. Each image is sent to the **Google Vision API**.
7. Google Vision returns a JSON response containing:
   - The full extracted text.
   - A hierarchical structure: `pages → blocks → paragraphs → words → symbols`, each with bounding-box coordinates.
   - Down to **single-character bounding boxes**.
8. The full JSON is persisted to a separate S3 bucket.
9. The status flag in the queue table is updated.

### Stage 2 — Brand identification (DMR custom code)
10. The brand identification engine (custom code by **Alberto Tornielli + Massimiliano**) consumes the Google Vision JSON.
11. It iterates **character by character** (via a for-loop through the full symbol stream, including spaces, underscores, dollar signs, and other punctuation).
12. It rebuilds the linear text flow from the hierarchical JSON and attempts to merge fragments that belong to the same article (heuristics on column adjacency).
13. It matches text fragments against the **brand alias list** maintained internally.
14. For each match, it writes:
    - To `Image_Brand` (one row per detected brand per image): `brand_id`, `image_id`.
    - To `Image_Brand_Word` (one row per matched word): `brand_id`, `image_id`, the exact matched word, and the bounding-box coordinates inside the image.
15. The bounding-box coordinates power the **yellow highlight rectangle** that operators see on the image preview in the Web Digital UI.

---

## 2. Key Points

| Area | Detail |
|---|---|
| **Pipeline application name** | "Print Image Management" — internal app used by the digitalization team. |
| **OCR engine in use** | Google Vision API (commercial). Alberto: "honestly, very good" on character recognition; weak on reading-order reconstruction. |
| **Pipeline architecture** | Two distinct stages: Stage 1 = third-party OCR (Google Vision); Stage 2 = DMR custom brand-alias matcher. The two stages are decoupled (Stage 1 output is persisted to S3 before Stage 2 reads it). |
| **Authorship of Stage 2** | Alberto Tornielli + Massimiliano. Written in DMR code that loops symbol-by-symbol through Google Vision's JSON. |
| **Volume / cost** | ~4 million images per year processed via Google Vision. Material recurring cost line. |
| **Output coordinates** | Bounding boxes are produced at the single-character level by Google Vision and propagated through Stage 2 down to per-matched-word coordinates. These coordinates are essential for the operator UI (yellow highlight rectangle). |
| **Reading-order limitation** | Google Vision splits text into blocks based on whitespace alone. No semantic/layout understanding. On magazines (single-flow articles) this works well; on newspapers and multi-column layouts the article is fragmented in arbitrary order. |
| **Multi-word brand splits** | When a multi-word brand spans two columns (e.g., "Van" / "Cleef"), each fragment is parsed as a separate block. Stage 2 alias matching fails. Single-word brands (Gucci, Prada) are unaffected. |
| **Mariana question — does block order matter for Stage 2?** | No. Stage 2 matches by content, not by sequence. Block order matters only when a multi-word brand is split across blocks. |
| **Coexistence with future LLM/AI roadmap** | Per Mariana (citing Margot): the current OCR pipeline **stays in operation** even after broader LLM/AI is added. Discover uses OCR text content for **keyword search inside print articles** (live client capability). Any new AI layer must be additive. |
| **Open-source OCR evaluation** | Suril has built a switchable framework (configuration-driven model swap) and run initial open-source benchmarks. Initial results: less accurate than Google Vision on title/content/brand/product extraction. Framework remains in place for further benchmarking. |
| **LLM as Stage 1.5** | Alberto's view: applying an LLM **to the Google Vision JSON output** (not as a replacement) could reconstruct correct article reading order and resolve the multi-column brand-split problem. Highest-leverage near-term improvement. |
| **Replacement constraint** | Any future OCR replacement (open-source or otherwise) must produce per-word/per-character bounding boxes. Without coordinates, the Stage 2 alias matcher and the operator-side yellow-highlight UI both break. |

---

## 3. Pain Points

### A. Data Entry Complexity

| Pain Point | Impact |
|---|---|
| **Multi-word brands split across columns are missed** | Newspapers and multi-column magazine layouts fragment "Van Cleef", "Patek Philippe", etc. across blocks. Stage 2 alias matcher fails. Operator may miss brand mentions that should have been pre-flagged. |

### B. Process / Procedure

| Pain Point | Impact |
|---|---|
| **Stage 2 brand matcher is character-by-character custom code** | Hard to maintain, hard to extend (e.g., for non-Western scripts), no semantic awareness. Logic for column merging and reading order is heuristic and not always correct. |
| **Brand alias list is the single source of truth for detection** | Quality of detection depends entirely on alias list completeness and quality. No vision-based / logo-based fallback. Adding a brand requires updating the list. |

### C. Dependencies on Other Teams / Vendors

| Pain Point | Impact |
|---|---|
| **Recurring Google Vision cost** | ~4M images/year through commercial API. Cost is a meaningful line item and a key driver for evaluating open-source replacements. |
| **Replacement constrained by coordinate-output requirement** | Any future Stage 1 replacement must emit per-character/per-word bounding boxes; this filters out OCR options that return only plain text. |

---

## 4. Easily Automatable Opportunities

### Medium-term (OCR / text extraction)

| Opportunity | Mechanism |
|---|---|
| **LLM-assisted reading-order reconstruction (post-Google-Vision)** | Pass the Google Vision JSON through an LLM that reconstructs the correct article flow on multi-column layouts. Resolves the dominant Stage 2 failure mode. Alberto identifies this as the highest-leverage near-term improvement. Operates on existing Stage 1 output → no replacement of Google Vision needed. |
| **Open-source OCR benchmark + cost reduction** | Continue Suril's benchmark framework. Compare candidates against Google Vision on representative DMR image set across publication types (magazine, newspaper, daily). Decision criteria: accuracy parity on character recognition + bounding-box fidelity + measurable cost reduction. |
| **Extend brand alias dictionary to non-Western scripts** | Cyrillic, Arabic, CJK brand variants. Independent of Stage 1 choice — can be done immediately on the current pipeline. **Same opportunity as P_ocr in dmr-process-knowledge.md, prioritized by Francesca.** |

### Longer-term (AI-assisted)

| Opportunity | Mechanism |
|---|---|
| **Vision-based brand detection (logo + printed text)** | Move beyond keyword/alias matching to image-based brand recognition. Higher precision, language-agnostic, fewer false positives. Prerequisite for reliable mail quotidiana automation per Francesca (Session 4). Strategic, not near-term. |
| **End-to-end semantic article extraction** | LLM-based extraction of article boundaries, captions, body, credits — replacing the current heuristic block-merging logic in Stage 2. |

---

## 5. Strategic Takeaways

**The OCR pipeline is a two-stage system, not a single system.** Stage 1 (Google Vision) is interchangeable in principle; Stage 2 (DMR brand alias matcher) is custom code that downstream teams depend on. Improvements to Stage 1 (LLM reading-order, open-source replacement) and Stage 2 (multilingual aliases, vision-based detection) are largely independent and can proceed in parallel.

**LLM-assisted reading-order reconstruction is the most promising near-term improvement.** It addresses the dominant Stage 2 failure mode (multi-column brand splits) without replacing Google Vision and without changing the operator UI contract (bounding-box coordinates are preserved). Alberto frames this as the most leveraged use of LLM capability in the print pipeline.

**The OCR pipeline must stay live regardless of broader AI roadmap.** Discover's keyword search inside print articles depends on the existing OCR text output. Any new AI layer is additive, not a replacement. This is a hard constraint from product (Margot).

**Open-source OCR evaluation is cost-driven, not accuracy-driven.** Alberto considers Google Vision very good on character recognition. The driver is the ~4M image/year commercial cost. Initial open-source tests have not matched Google Vision on accuracy — further benchmarking required before any switch is justifiable. The switchable framework Suril has built makes future benchmarks fast.

**Process action item (Mariana):** schedule a follow-up dedicated to the LLM reading-order experiment with Suril once he has demoed his open-source OCR test results.
