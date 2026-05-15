#!/usr/bin/env bash
# Start the mlx-vlm server serving GLM-OCR on Apple Silicon.
#
# Runs alongside the project's PaddleOCR-VL MLX server (default port 8111) —
# this one defaults to 8112 to avoid the clash.
#
# Usage:
#   ./start_server.sh [port]
#
# Expects .venv-server/ to exist (see README.md for setup).

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${1:-8112}"
MODEL="${MLX_VLM_MODEL:-mlx-community/GLM-OCR-bf16}"
VENV_DIR="${HERE}/.venv"

if [[ ! -x "${VENV_DIR}/bin/mlx_vlm.server" ]]; then
  echo "mlx_vlm.server not found in ${VENV_DIR}."
  echo "Set up the server venv first — see README.md."
  exit 1
fi

# Prepend timestamps so log files are readable.
LOG_DIR="${HERE}/logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/mlx_glm_ocr.log"

exec > >(python3 -u -c '
import sys, time
for line in sys.stdin:
    sys.stdout.write(time.strftime("%Y-%m-%d %H:%M:%S%z") + " | " + line)
    sys.stdout.flush()
' | tee -a "${LOG_FILE}") 2>&1

echo "GLM-OCR MLX server starting (pid=$$, port=${PORT}, model=${MODEL})"
echo "SDK config: api_port=${PORT}, model=${MODEL}, api_path=/chat/completions"

on_exit() {
  local code=$?
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  echo "GLM-OCR MLX server stopped (exit=${code}, pid=$$)"
}
trap on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

"${VENV_DIR}/bin/mlx_vlm.server" \
  --trust-remote-code \
  --model "${MODEL}" \
  --port "${PORT}" &
SERVER_PID=$!
echo "GLM-OCR MLX server started (server_pid=${SERVER_PID})"
wait "$SERVER_PID"
