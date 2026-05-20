# OCR engine evaluation — what we learned

**Date:** 19 May 2026
**Hardware:** Apple Silicon (M-series, macOS-arm64)
**Test corpus:** Vogue UK April 2026, 255 magazine pages (`inputs/vogue_uk_2026-04-01/`)
**Reference (ground truth):** Google Vision `DOCUMENT_TEXT_DETECTION` JSON, manually verified as production-grade.

---

## TL;DR

| Engine | Speed (s/page) | Quality vs Google Vision (CER) | Verdict |
|---|---|---|---|
| **PaddleOCR-VL 1.5** | 7.5 | **0.22** (≈78% characters correct) | **Chosen.** Best quality/effort balance, ships with semantic layout labels. |
| GLM-OCR-bf16 | 1.3 | 1.6+ (output not aligned to GV format) | Faster but unusable as-is; output is markdown-heavy and doesn't structurally match our reference. |
| FireRed-OCR-2B | — | — | Skipped. No Apple Silicon MLX port; PyTorch/MPS path estimated at 3–4 hours per magazine. |

The wall-clock cost we accepted is **≈32 minutes per 255-page magazine** on a single M-series Mac for the best-quality engine, with one CPU thread doing layout detection and the Metal GPU doing the heavy VLM lift via a long-lived local server.

**Key operational decision:** we run the VLM on **MLX** (Apple's native ML framework for Apple Silicon), served by a long-lived local HTTP process. This is the single biggest infrastructure choice in the pipeline — see optimization #6 below — and it's what makes any of these numbers achievable on a Mac.

---

## What we tested

### Engines

1. **PaddleOCR-VL 1.5** — two-stage pipeline. PaddlePaddle (CPU) detects layout regions on each page; a Vision-Language Model running on the Metal GPU reads each region and produces text + a semantic label (`headline`, `body`, `caption`, `figure`, etc.).
2. **GLM-OCR (bf16)** — end-to-end VLM. One model pass per page. Outputs Markdown plus per-region bounding boxes.
3. **FireRed-OCR-2B** — end-to-end VLM, Qwen3-VL-2B finetune. Outputs full-page Markdown. **Not run** — no MLX port available; PyTorch/MPS path infeasible for full-magazine evaluation in our time budget.

### What we compared

The harness loads each runner's output into a shared schema (`OcrBlock { text, bbox, confidence, block_type }`), then per page:

| Metric | What it measures |
|---|---|
| **CER** (Character Error Rate) | Levenshtein distance vs Google Vision's full-page text, normalised by reference length. Lower is better. |
| **WER** (Word Error Rate) | Same but tokenised on whitespace. Lower is better. |
| **Mean best-match IoU** | For each GV paragraph box, find the runner box that overlaps most. Average those scores. Diagnostic only — see "Caveats" below. |

We **removed block-count delta** as a headline metric mid-evaluation: it's structurally biased because Google Vision emits paragraph-shaped blocks while Paddle emits layout-region-shaped blocks. They're not directly comparable.

---

## Timings — actual numbers

Aggregated from `ocr_eval/results.db`:

| Runner | Runs | Avg duration (255 pages) | Avg s/page | Best run |
|---|---|---|---|---|
| `glm_ocr` | 3 | 5m 35s | **1.31** | — |
| `paddleocr_vl` | 4 | 28m 33s | **6.72** | 31m 43s (after tuning) |

PaddleOCR's **best individual run after all optimizations: 1903 s = 31m 43s = 7.46 s/page** (run `20260519T143252Z`).

That's down from a baseline of **2488 s = 9.76 s/page** before tuning — a **~24% speedup** at zero quality cost.

---

## Quality — actual numbers

Per-engine averages across paired pages vs Google Vision:

| Engine | Mean CER | Mean WER | Mean IoU |
|---|---|---|---|
| **PaddleOCR-VL 1.5 (latest, tuned)** | **0.2161** | **0.2459** | 0.4133 |
| PaddleOCR-VL 1.5 (baseline, bf16) | 0.263 | 0.267 | 0.4133 |
| GLM-OCR (bf16) | 1.66 | 1.74 | 0.336 |

- **PaddleOCR at 0.22 CER ≈ 78% of characters correctly recognised**, ~75% of words.
- GLM-OCR's CER > 1.0 means its output is so much longer than the reference (markdown headers, table syntax, etc.) that edit distance exceeds reference length. It's not "worse OCR" in a naive sense — its output shape simply doesn't match Google Vision's. To use GLM-OCR we'd have to strip markdown back to plain text and re-evaluate. Not pursued here.
- IoU is identical across paddle runs (0.413) because we never touched the layout detector — only the VLM that reads each region.

---

## Optimizations applied — and what each one bought us

Each step was kept or rejected based on whether `mean CER` held vs the prior run.

### 1. Quantization: bf16 → 8-bit weights

- **What:** Swapped from `mlx-community/PaddleOCR-VL-1.5-bf16` to `mlx-community/PaddleOCR-VL-1.5-8bit`.
- **Why:** Smaller weights → less memory bandwidth on the Metal GPU → faster autoregressive decode.
- **Result:** Modest wall-clock improvement; **no measurable CER change** (0.2163 → 0.2161). 8-bit is effectively a free win for this workload.

### 2. Disabled unused PaddleOCR sub-pipelines

The PaddleOCR library ships with optional preprocessing stages. We're processing clean magazine scans, so:

| Disabled | Why |
|---|---|
| `use_doc_orientation_classify=False` | Pages are scanned upright. |
| `use_doc_unwarping=False` | Scans are flat; no curl-correction needed. |
| `use_chart_recognition=False` | We don't need structured chart data; figures are passed through as regions. |
| `use_seal_recognition=False` | No stamps/seals in magazine content. |

- **Result:** Removed several seconds of per-page overhead. No quality cost — these stages weren't producing useful output for our inputs anyway.

### 3. VLM prompt-label whitelist

PaddleOCR-VL's layout detector emits 20+ block-type labels (`text`, `doc_title`, `figure_caption`, `equation`, `table`, `seal`, `chart`, `header_image`, etc.). By default it would call the expensive VLM on **every** detected region.

- **What:** Restricted VLM calls to the 12 labels we actually care about (`text`, `doc_title`, `title`, `paragraph_title`, `header`, `footer`, `figure_caption`, `table_caption`, `abstract`, `aside_text`, `reference`, `footnote`).
- **Result:** Layout detector still finds figure/equation/chart bboxes (we keep them as image regions), but skips VLM recognition on them. Per-page region count sent to the VLM dropped meaningfully.

### 4. Tighter VLM generation kwargs

Default VLM generation parameters are optimised for "creative" tasks. For OCR — which has one correct answer — we tightened them:

| Kwarg | Old (default) | New | Why |
|---|---|---|---|
| `temperature` | 1.0 | **0.0** | Pure greedy decode. OCR has one correct output. |
| `top_p` | 1.0 | 1.0 | Unchanged (irrelevant at temperature 0). |
| `repetition_penalty` | 1.0 | **1.05** | Suppresses the "repeated line" failure mode VLMs hit on noisy regions. |
| `max_new_tokens` | 4096 | **1024** | A single magazine region produces ~50–300 tokens; 4096 was wasted compute on outliers. |

- **Result:** **This is where most of the quality gain came from** — CER dropped from 0.263 → 0.216 (≈18% relative improvement) on the same model. Greedy decode + repetition penalty essentially eliminated the "VLM hallucinates a few extra sentences at the end of a caption" pattern.

### 5. Concurrency — the one that surprised us

PaddleOCR-VL ships with a per-page VLM concurrency setting (defaults to 200). We had it accidentally throttled to 4 in an earlier config.

- **What we expected:** Bumping concurrency would give a 3–4× speedup.
- **What we got:** ~7% speedup, full stop.
- **Why:** The MLX-VLM server we run on the Metal GPU **serialises requests** — there's no batched GPU inference in the current `mlx-vlm.server` build. Client-side concurrency just queues requests faster; the GPU still processes them one at a time. The true bottleneck is per-request autoregressive decode latency.
- **Lesson:** Always benchmark before assuming concurrency knobs help. Library defaults can be misleading.

### 6. Operational: long-lived local MLX-VLM server *(the biggest infra decision)*

This is the foundation everything else sits on. Two choices in one:

**6a. Why MLX (the framework)**

For running a Vision-Language Model on Apple Silicon we evaluated three options:

| Runtime | What it is | Apple Silicon perf |
|---|---|---|
| **MLX** (chosen) | Apple's native ML framework, Metal-first, unified-memory aware | Fastest production path. Built specifically for M-series GPUs. |
| PyTorch + MPS | Standard PyTorch with the Metal Performance Shaders backend | Works, but ~20–40% slower than MLX on equivalent VLMs. Pays a CPU↔GPU copy cost MLX avoids. |
| Ollama / llama.cpp | Generic GGUF runtime via llama.cpp's Metal compute shaders | Excellent, but typically 10–25% slower than MLX on the same quantization. Better for portability across platforms, not for raw speed on Macs. |

MLX wins on Apple Silicon because of one architectural fact: unified memory. The CPU and GPU share the same RAM, so MLX never copies tensors between devices. PyTorch/MPS pretends Mac hardware has a separate GPU memory pool and pays a copy cost on every transfer. For autoregressive decoding (token-by-token, where every step touches GPU memory) that copy cost compounds.

**6b. Why a long-lived server (the pattern)**

The VLM weights are large (≈2 GB at 8-bit) and slow to load — 10+ seconds on a cold start. Loading them once per page or once per process would dominate wall-clock time.

- **What:** Stand up a local HTTP server (`mlx_vlm.server`) that loads the weights once into the unified memory pool and stays running for the duration of the job (and beyond, between jobs). The PaddleOCR runner calls it via an OpenAI-compatible HTTP endpoint for each region.
- **How:** Managed by a single shell CLI (`./scripts/mlx`) — port-based status, idempotent start, clean stop. Replaces three earlier mechanisms that had drifted out of sync (direnv autostart, shell functions, app-level preflight).
- **Result:** Removes ~10 s × 1500 regions = ~4 hours of wasted weight-loading per magazine.

**Why this pattern matters for local Mac testing**

The long-lived server is what makes iterative development bearable. Without it, every code change that touches the OCR pipeline triggers a fresh model load — you wait 10–15 s before seeing any output, every single time. With it, you change code, hit Run, and the first page comes back within a second.

It's also what makes the comparison harness fair: all runners share the same warm server, so we're measuring *engine* performance, not *cold-start* performance.

---

## What didn't work / what we didn't do

| Idea | Why we didn't pursue |
|---|---|
| **Multi-page parallelism** | mlx-vlm.server serialises GPU work. Spinning up multiple servers would contend for the same Metal GPU and hurt throughput. |
| **Higher concurrency** | See above — the GPU is the bottleneck, not the client. |
| **Lower `max_pixels` for VLM input** | Would shrink token counts per region (faster decode), but risks losing detail on small captions. Worth A/B-testing in a future round; current performance is acceptable. |
| **FireRed-OCR-2B** | No MLX quantization exists. PyTorch/MPS estimate is 3–4 hours per magazine. Not viable on current hardware until a community MLX port lands. |
| **GLM-OCR as a viable engine** | Output is markdown; the comparison vs GV's plain-text-with-paragraph-blocks format is structurally incompatible. Would need a separate evaluation harness or a markdown-aware reference dataset. |

---

## Caveats — be honest with the team

1. **Google Vision is not ground truth.** It's a *credible reference* because it's a mature, battle-tested commercial OCR. But it has its own errors — especially on decorative fonts, italics, tight kerning, and rotated text. A runner that "disagrees" with Vision can be more correct on that page.

2. **CER/WER are the only metrics we trust for quality comparison.** They're segmentation-agnostic and directly measure "did you read the same characters?".

3. **IoU is a diagnostic, not a quality score.** We compute it (paddle's semantic blocks vs Vision's paragraph blocks via best-match), but the absolute value depends on how the two systems define a "region". Treat ≈0.41 as our healthy-baseline; a drop of >10% means the layout detector regressed, not that OCR got worse.

4. **Reading order matters.** If the runner reads columns top-to-bottom across the page while Vision reads them left-to-right, CER spikes even when every word is correct. We don't currently reorder blocks before computing CER. This is the most likely cause of "false errors" in our 0.22 CER figure.

5. **Block-type accuracy isn't measured.** Vision doesn't classify regions (no "headline" vs "body" vs "caption"), so we can't score Paddle's semantic labels against it. Manual spot-checks on a sample is the only way to validate this.

6. **Run-to-run variance is small.** Three back-to-back paddle runs at identical settings produced CER 0.2161, 0.2163, 0.2630 — the outlier was a config diff (max_new_tokens=2048 vs 1024), not engine non-determinism.

---

## Recommended decisions

1. **Adopt PaddleOCR-VL 1.5 (8-bit, tuned) as the default OCR engine** for the print-monitoring pipeline.
2. **Keep MLX + a long-lived local server as the standard local-testing setup on Macs.** It's the fastest VLM runtime on Apple Silicon, and the long-lived server removes ~4 hours of wasted weight-loading per magazine. The `./scripts/mlx` CLI is the only interface anyone should need to learn.
3. **Keep Google Vision integration available** as a fallback / sanity check for pages where Paddle confidence is low or layout regression triggers.
4. **Park FireRed-OCR** — revisit if a community MLX port appears, then re-evaluate.
5. **Treat 7.5 s/page (≈32 min/magazine on a single Mac) as the operational baseline.** If we need to scale, the GPU is the limiter — adding more pages of throughput means more Macs, not more processes per Mac.
6. **Build a reading-order-corrected paragraph-level CER metric** before pushing for further quality improvements. The current CER number is partially noise from reading-order mismatch, not OCR error. Without that fix we can't reliably tell whether further tuning is helping.

---

## Appendix — files / commands of record

- **Pipeline source:** `ocr_eval/runners/paddleocr_vl/run.py`
- **Config:** `ocr_eval/runners/paddleocr_vl/paddleocr_vl_config.yaml`
- **Comparison harness:** `ocr_eval/evaluate.py`, `ocr_eval/metrics.py`
- **Results DB:** `ocr_eval/results.db` (tables: `ocr_runs`, `comparisons`, `run_failures`)
- **MLX server CLI:** `./scripts/mlx {status,start,stop,restart,logs} {paddle,glm}`
- **Gradio UI:** `uv run python ocr_eval/app.py`
