#!/usr/bin/env bash
# Start the MLX-VLM server that serves PaddleOCR-VL on Apple Silicon GPU.
# Run this in a separate terminal BEFORE launching the pipeline,
# or let .envrc auto-start it (writes to logs/mlx_server.log).
#
# Usage: ./scripts/start_mlx_server.sh [port]

set -uo pipefail

PORT="${1:-8111}"
# Quantization options (smaller = faster, less accurate):
#   mlx-community/PaddleOCR-VL-1.5-bf16   (full precision)
#   mlx-community/PaddleOCR-VL-1.5-8bit   (default — ~1.5-2x faster, near-bf16 accuracy)
#   mlx-community/PaddleOCR-VL-1.5-6bit
#   mlx-community/PaddleOCR-VL-1.5-5bit
#   mlx-community/PaddleOCR-VL-1.5-4bit
MODEL="${MLX_VLM_MODEL:-mlx-community/PaddleOCR-VL-1.5-8bit}"

# Prepend ISO-8601 timestamps to every line of stdout/stderr so the
# log file (logs/mlx_server.log) is readable alongside pipeline.log.
# python -u keeps the filter unbuffered.
exec > >(python3 -u -c '
import sys, time
for line in sys.stdin:
    sys.stdout.write(time.strftime("%Y-%m-%d %H:%M:%S%z") + " | " + line)
    sys.stdout.flush()
') 2>&1

# Log a clear stop marker no matter how the server exits (Ctrl-C,
# SIGTERM from `./scripts/mlx stop`, child crash). EXIT fires after INT/TERM too.
on_exit() {
  local code=$?
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  echo "MLX-VLM server stopped (exit=${code}, pid=$$)"
}
trap on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if ! command -v mlx_vlm.server >/dev/null 2>&1; then
  echo "mlx_vlm.server not found. Install with: uv pip install -e \".\""
  echo "(mlx-vlm is included as a macOS-arm64 dep in pyproject.toml)"
  exit 1
fi

echo "MLX-VLM server starting (pid=$$, port=${PORT}, model=${MODEL})"
echo "Configure config.yaml with:"
echo "    vl_rec_backend: \"mlx-vlm-server\""
echo "    vl_rec_server_url: \"http://localhost:${PORT}/v1\""
echo "    vl_rec_api_model_name: \"${MODEL}\""

# Run as a child (not exec) so the EXIT trap can fire and emit the
# "stopped" line. `wait` blocks until the child exits or a signal
# triggers the traps above.
mlx_vlm.server --model "${MODEL}" --port "${PORT}" &
SERVER_PID=$!
echo "MLX-VLM server started (server_pid=${SERVER_PID})"
wait "$SERVER_PID"
