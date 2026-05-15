# PaddleOCR-VL runner

Two ways to produce normalised output for this runner. Pick one.

## Option A: standalone runner (recommended for fresh evaluation)

Runs `paddleocr.PaddleOCRVL` directly. No dependency on `open_src/`. Layout
detection runs locally via PaddlePaddle; the VLM recognition stage is
offloaded to a local mlx-vlm server on port **8111** (shared with the
production pipeline).

### One-time setup

```bash
cd ocr_eval/runners/paddleocr_vl
chmod +x setup.sh
./setup.sh
```

Creates `./.venv/` with `paddlepaddle`, `paddleocr[doc-parser]`, `pyyaml`,
`Pillow`, `numpy`.

### Make sure the MLX server is running

The runner expects `http://localhost:8111/v1` to be serving
`mlx-community/PaddleOCR-VL-1.5-bf16`. The project's `direnv` setup starts
this for you when you `cd` into the workspace. Manual start:

```bash
./scripts/start_mlx_server.sh
```

(Check with `curl -s http://localhost:8111/v1/models | head`.)

### Run against a single image

```bash
cd ocr_eval/runners/paddleocr_vl
.venv/bin/python run.py \
  --input ../../../inputs/vogue_uk_2026-04-01/00000041.jpg \
  --output ../../outputs/paddleocr_vl/00000041.json
```

### Loop over a folder

```bash
cd ocr_eval/runners/paddleocr_vl
for img in ../../../inputs/vogue_uk_2026-04-01/*.jpg; do
  stem=$(basename "$img" .jpg)
  .venv/bin/python run.py --input "$img" --output "../../outputs/paddleocr_vl/${stem}.json"
done
```

### Config

[paddleocr_vl_config.yaml](paddleocr_vl_config.yaml) — change the MLX URL,
model name, or fall back to local CPU by clearing `vl_rec_backend`.

## Option B: convert existing pipeline output (no model re-run)

If the production pipeline in `open_src/` has already processed your images,
just translate its JSON into the normalised schema. No GPU needed.

```bash
cd ocr_eval
uv run python runners/paddleocr_vl/convert.py \
  --pipeline-output ../open_src/output/vogue_uk_2026-04-01_20260506T114730/
```

Either accept a single JSON file or a folder. Outputs land in
`ocr_eval/outputs/paddleocr_vl/<stem>.json`.

## Then compare

```bash
cd ocr_eval
uv run python compare.py --runner paddleocr_vl
```

## Output contents

Each output JSON matches [`schema.OcrOutput`](../../schema.py):

- `blocks` — text regions with `text`, `bbox`, `block_type`.
- `image_regions` — non-text regions (figures, photos, charts) with
  `bbox` and `region_type`. These are what OWLv2 would later crop for
  zero-shot detection in the production pipeline.
- `source_image_path` — absolute path to the original JPG/PNG.

## Troubleshooting

- **`Connection refused` / fallback to CPU** — the MLX server isn't on port
  8111. Start it via `scripts/start_mlx_server.sh` or comment out the
  `vl_rec_*` lines in the config to run PaddlePaddle locally (slow).
- **Big memory footprint** — PaddlePaddle loads ~500 MB of layout weights
  on first call. Subsequent calls in the same process are fast.
- **Different metrics from the production pipeline on the same image** —
  expected: both paths use the same model, but the standalone runner may
  apply normalisation slightly differently. Treat the bigger gap as a real
  hint and investigate.
