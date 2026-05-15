#!/usr/bin/env bash
# Create a self-contained venv for the standalone PaddleOCR-VL runner.
#
# Usage:
#     ./setup.sh
#
# After this, run.py uses ./.venv/bin/python and pulls deps from here only.
# The MLX-VLM server (port 8111) is shared with the production pipeline —
# this runner doesn't need to start its own.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${HERE}/.venv"

if [[ -d "${VENV_DIR}" ]]; then
  echo "venv already exists at ${VENV_DIR}; remove it first if you want a clean rebuild."
  exit 0
fi

cd "${HERE}"
uv venv "${VENV_DIR}" --python 3.12

# Pin the venv explicitly so uv doesn't walk up the tree and install into the
# project-root .venv by mistake.
VIRTUAL_ENV="${VENV_DIR}" uv pip install \
  "paddlepaddle" \
  "paddleocr[doc-parser]" \
  "Pillow" \
  "numpy" \
  "pyyaml"

echo
echo "Done. Activate with:  source ${VENV_DIR}/bin/activate"
echo "Or just call:         ${VENV_DIR}/bin/python run.py --input ... --output ..."
