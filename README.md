# Print Document Intelligence Pipeline

## Quick Start

### 1. Install dependencies

```bash
uv venv && uv pip install -e "."
uv run python -m spacy download en_core_web_trf
```

On Apple Silicon, `mlx-vlm` is installed automatically as part of `pip install -e "."`.

### 2. MLX-VLM server (Apple Silicon only) — auto-started by direnv

The default config offloads PaddleOCR-VL's heavy VLM recognition to a local MLX-VLM server running on the Apple GPU. **You don't need to start it manually** — `.envrc` boots it in the background the first time you `cd` into the project (or run `direnv reload`). Subsequent shells reuse the running instance.

The server downloads ~1.7 GB of weights on first launch and listens on port `8111`.

**Verify it's up:**

```bash
mlx_server_running           # prints "running (port 8111)" or "not running"
tail -f logs/mlx_server.log  # see startup output and request logs
```

`mlx_server_running` probes `http://localhost:$MLX_VLM_PORT/health` — it
only reports "running" once the API is actually serving requests, not just
when the wrapper process has spawned. (The model takes ~2 min to load on
first start, during which the process is alive but the server isn't ready
yet.) The function also returns the appropriate exit code, so it still
composes with `&&` / `||` and `if` if you want to script against it.

You can also open
[http://localhost:8111/docs](http://localhost:8111/docs) in a browser — if
the Swagger page loads, the server is up. Hitting `/` will return 404 by
design; MLX-VLM only exposes API routes.

**Stop it:**

```bash
mlx-stop
```

**Restart with a different quantization (smaller, faster, less accurate):**

```bash
mlx-stop
MLX_VLM_MODEL=mlx-community/PaddleOCR-VL-1.5-4bit direnv reload
# or 5bit / 6bit / 8bit — see scripts/start_mlx_server.sh for the full list
```

**Use a different port:**

```bash
mlx-stop
MLX_VLM_PORT=9000 direnv reload
# also update vl_rec_server_url in config.yaml to match
```

**Manual start (if you've disabled direnv or aren't on Apple Silicon):**

```bash
./scripts/start_mlx_server.sh
```

**Skip the MLX server entirely (CPU-only, slower):** comment out the `vl_rec_*` lines under `models.ocr` in `config.yaml`. The auto-start is harmless if you do this — the server will just sit idle.

### 3. Run on a single file

In a second terminal:

```bash
uv run python main.py --input path/to/scan.jpg
```

### 4. Run on a folder of scans

```bash
uv run python main.py --input ./inputs/
```

Supported formats: `.jpg`, `.jpeg`, `.png`, `.pdf`

## Workflow at a glance

```
direnv (on cd into project)        Your terminal
──────────────────────────         ───────────────────────────────
auto-starts MLX-VLM server         uv run python main.py -i …
in the background                     ↓
   ↓                               PaddleOCR-VL backend
MLX-VLM server on :8111  ◀───────  (PaddlePaddle layout det. on CPU)
(Apple GPU — recognition)             ↓
logs → logs/mlx_server.log         OWLv2 + LayoutLMv3 (MPS)
pid   → .mlx_server.pid            spaCy NER (CPU)
                                      ↓
                                   output/<file>_<timestamp>_<models>.json
```

The MLX server keeps running until you call `mlx-stop` or kill the PID. Re-entering the directory in a new shell reuses it — no duplicate processes.

## CLI Options

```
uv run python main.py --input <file_or_folder> [options]

Required:
  --input, -i        Path to an image file, PDF, or folder of scans

Optional:
  --output, -o       Output directory (default: output/)
  --config, -c       Path to config file (default: config.yaml)
  --log-level        DEBUG | INFO | WARNING | ERROR
  --ocr-model        Override OCR backend
  --layout-model     Override layout model
  --ner-model        Override NER model
  --image-model      Override image analysis model
```

## Examples

```bash
# Process a single JPEG with debug logging
uv run python main.py -i magazine_cover.jpg --log-level DEBUG

# Process a multi-page PDF
uv run python main.py -i newspaper.pdf

# Process a folder, output to a custom directory
uv run python main.py -i ./scans/ -o ./results/

# Use a custom config file
uv run python main.py -i scan.png -c my_config.yaml
```

## Output

Results are written as JSON files to the `output/` folder (or the directory specified with `--output`). Successfully processed inputs are moved to `processed/` so a re-run only picks up new files.

Filenames follow the pattern:
```
<input_name>_<timestamp>_<models>.json
```

Example: `magazine_cover_2026-04-23T14-30-00_paddleocr_vl_paddleocr_vl_spacy_owlv2.json`

## Configuration

Edit `config.yaml` to change models, detection prompts, or output settings. CLI arguments override config file values.

### Available OCR backends

- `paddleocr_vl` (**default**) — PaddleOCR-VL-1.5, 0.9B vision-language model. Best accuracy, GPU-accelerated via the MLX server on Apple Silicon.
- `ppstructure` — PaddleOCR PP-StructureV3, the older multi-stage pipeline. Lighter, runs on CPU at usable speed if you don't want to deal with the MLX server.
- `doctr` — DocTR, OCR-only. Pair with `layoutlmv3` (or its heuristic fallback) for the layout stage.

To switch:

```yaml
models:
  ocr:
    backend: "ppstructure"   # or "doctr" / "paddleocr_vl"
    model_name: "en"
  layout:
    backend: "ppstructure"   # match the OCR backend if it's combined, or "layoutlmv3"
```

## Hardware notes

- **Apple Silicon (M1+)**: OWLv2 and LayoutLMv3 run on MPS automatically. PaddleOCR-VL recognition runs on Apple GPU via the MLX server. PaddlePaddle's local layout detection runs on CPU (small model, fast).
- **CUDA GPU**: Set `use_gpu: true`-equivalent paths via PaddlePaddle's `device="gpu"` (already auto-detected for OWLv2/LayoutLMv3 via PyTorch). The MLX server is not needed — comment out the `vl_rec_*` lines in `config.yaml`.
- **CPU only**: Works. PaddleOCR-VL will be the bottleneck — consider switching to `ppstructure` for batch throughput.

If you hit an unsupported MPS op on OWLv2 / LayoutLMv3:

```bash
PYTORCH_ENABLE_MPS_FALLBACK=1 uv run python main.py -i ./inputs/
```
