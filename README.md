# Print Document Intelligence Pipeline

## Quick Start

### 1. Install dependencies

```bash
uv venv && uv pip install -e "."
uv run python -m spacy download en_core_web_trf
```

On Apple Silicon, `mlx-vlm` is installed automatically as part of `pip install -e "."`.

### 2. MLX-VLM servers (Apple Silicon only)

The default config offloads VLM recognition (PaddleOCR-VL, GLM-OCR) to local
`mlx-vlm.server` instances running on the Apple GPU. They are managed by one
small CLI — `./scripts/mlx` — and the Gradio app starts them on demand when
you click **Run**, so most of the time you don't need to think about them.

| Server | Port | Default model |
|---|---|---|
| `paddle` | 8111 | `mlx-community/PaddleOCR-VL-1.5-8bit` |
| `glm`    | 8112 | `mlx-community/GLM-OCR-bf16` |

Each server downloads ~1–2 GB of weights on first launch.

**Common commands** (work from any shell, no direnv required):

```bash
./scripts/mlx status            # which servers are listening?
./scripts/mlx start paddle      # idempotent — exits 0 if already up
./scripts/mlx start glm
./scripts/mlx stop paddle       # kills whatever holds the port
./scripts/mlx stop all
./scripts/mlx restart paddle    # for picking up a new model name
./scripts/mlx logs paddle       # tail -F the log
```

The source of truth is the listening TCP port — no PID files, no shell-state
to go stale. `status` reports based on `lsof`, `start` waits up to 180s for
the port to open (the model takes a minute or two to load on first start).

**Switch to a different quantization** — edit `MODEL=` at the top of
`scripts/start_mlx_server.sh` (paddle) or
`ocr_eval/runners/glm_ocr/start_server.sh` (glm), then:

```bash
./scripts/mlx restart paddle
```

Available paddle quantizations: `bf16`, `8bit` (default), `6bit`, `5bit`, `4bit`.

**Skip the MLX server entirely** (CPU-only, slow): comment out the
`vl_rec_*` lines in `ocr_eval/runners/paddleocr_vl/paddleocr_vl_config.yaml`.

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
Your terminal                              ./scripts/mlx
─────────────────────────────              ──────────────────────────
uv run python main.py -i …                 status / start / stop / logs
   ↓                                       ↓
PaddleOCR-VL backend                       MLX-VLM server on :8111
(PaddlePaddle layout det. on CPU)  ◀─────  (Apple GPU — VLM recognition)
   ↓                                       logs → logs/mlx_server.log
OWLv2 + LayoutLMv3 (MPS)
spaCy NER (CPU)
   ↓
output/<file>_<timestamp>_<models>.json
```

The MLX servers keep running until you call `./scripts/mlx stop` or kill the
port. Re-running the app in a new shell reuses them — no duplicate processes.

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
