#!/usr/bin/env bash
# Set up the venv for the classic PaddleOCR runner.
#
# Dependencies are identical to paddleocr_vl (same `paddleocr` package,
# different sub-pipeline), so we symlink rather than duplicate ~2 GB of
# paddle/torch wheels. Run paddleocr_vl/setup.sh first.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_VENV="${HERE}/../paddleocr_vl/.venv"
VENV_LINK="${HERE}/.venv"

if [[ ! -d "${SHARED_VENV}" ]]; then
  echo "error: shared venv not found at ${SHARED_VENV}"
  echo "run ../paddleocr_vl/setup.sh first."
  exit 1
fi

if [[ -e "${VENV_LINK}" || -L "${VENV_LINK}" ]]; then
  echo ".venv already exists at ${VENV_LINK}; remove it for a clean rebuild."
  exit 0
fi

ln -s "../paddleocr_vl/.venv" "${VENV_LINK}"
echo "Symlinked ${VENV_LINK} -> ../paddleocr_vl/.venv"
echo "Test with: ${VENV_LINK}/bin/python run.py --input <image> --output out.json"
