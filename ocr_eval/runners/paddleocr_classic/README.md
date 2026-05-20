# Classic PaddleOCR runner

Wraps `paddleocr.PaddleOCR` (PP-OCRv5: text detection + recognition, both
CNN-based). Much faster than the VL variant — no VLM, no MLX server, pure
CPU pipeline — but produces:

- One block per detected **text line**, not per layout region.
- `block_type` is always `"text"` (no semantic labels — no headline/caption/etc).
- Lower quality on stylised / decorative fonts.

## Setup

```bash
# 1. Set up the shared paddleocr venv (only needed once for both runners)
cd ../paddleocr_vl && ./setup.sh && cd -

# 2. Link this runner to the same venv
./setup.sh
```

## Run

```bash
.venv/bin/python run.py --input <image_or_folder> --output-dir ../../outputs/paddleocr_classic/<run_id>/
```

Or via the Gradio harness — it picks up any folder under `ocr_eval/runners/`
with a `run.py` and a `.venv`.
