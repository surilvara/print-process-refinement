# GLM-OCR runner (local Apple Silicon)

Runs GLM-OCR via mlx-vlm on the Metal GPU.

As of glmocr 0.1.5 and current mlx-vlm both depend on `transformers>=5.x`,
so a single venv works. (Earlier upstream docs called for two envs —
no longer needed.)

## One-time setup

```bash
cd ocr_eval/runners/glm_ocr
chmod +x setup.sh start_server.sh
./setup.sh
```

`setup.sh` creates `.venv` in this folder and installs everything into it.
It uses an explicit `VIRTUAL_ENV` so deps can never leak to the project's
root venv.

## Run it

In **terminal 1** (leave running):

```bash
cd ocr_eval/runners/glm_ocr
./start_server.sh                       # serves on port 8112
# logs: ocr_eval/runners/glm_ocr/logs/mlx_glm_ocr.log
```

First boot downloads `mlx-community/GLM-OCR-bf16` weights (~1.5 GB) and
compiles Metal shaders — subsequent runs are fast.

Quick health check:

```bash
curl -s http://localhost:8112/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"mlx-community/GLM-OCR-bf16","messages":[{"role":"user","content":[{"type":"text","text":"hello"}]}],"max_tokens":4}' | head -c 200
```

In **terminal 2**, run the runner against a single image:

```bash
cd ocr_eval/runners/glm_ocr
.venv/bin/python run.py \
  --input ../../../inputs/vogue_uk_2026-04-01/00000041.jpg \
  --output ../../outputs/glm_ocr/00000041.json
```

Or loop over a folder:

```bash
for img in ../../../inputs/vogue_uk_2026-04-01/*.jpg; do
  stem=$(basename "$img" .jpg)
  .venv/bin/python run.py --input "$img" --output "../../outputs/glm_ocr/${stem}.json"
done
```

## Compare against the Google Vision baseline

```bash
cd ../..   # back to ocr_eval/
uv run python compare.py --runner glm_ocr --csv results_glm_ocr.csv
```

## Coexistence with the production pipeline

- Port **8111** is reserved by the project's PaddleOCR-VL MLX server.
- Port **8112** is used here for GLM-OCR. Both servers can run side-by-side;
  Apple Silicon unified memory is shared, so total VRAM usage is the sum.

## Stopping the server

`Ctrl-C` in terminal 1 — the script's `EXIT` trap kills the child cleanly.

## Troubleshooting

- **`model glm_ocr not found`**: the PyPI mlx-vlm doesn't yet include the
  architecture — reinstall from git as above.
- **Connection refused**: `start_server.sh` not running or wrong port in
  `glmocr_config.yaml`.
- **First request slow**: Metal shader compilation. Warm with the curl
  health check before benchmarking.
