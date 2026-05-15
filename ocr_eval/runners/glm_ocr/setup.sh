#!/usr/bin/env bash
# Set up the glm_ocr runner's venv with all required dependencies.
# Run from this folder; idempotent — re-running upgrades pinned versions.

set -euo pipefail

cd "$(dirname "$0")"

uv venv .venv --python 3.12

# Install glmocr SDK (selfhosted = layout + Paddle) and mlx-vlm from git.
# mlx-vlm is pulled from git because the PyPI release may lag GLM-OCR
# architecture support. Switch to plain "mlx-vlm" once tagged upstream.
VIRTUAL_ENV="$PWD/.venv" uv pip install \
  "glmocr[selfhosted]" \
  "git+https://github.com/Blaizzy/mlx-vlm.git" \
  Pillow

echo "glm_ocr venv ready: $PWD/.venv"
echo "Next: ./start_server.sh   (in terminal 1)"
echo "      .venv/bin/python run.py --input <img> --output <json>  (in terminal 2)"
