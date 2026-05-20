"""Static configuration for the classifier module.

Edit values here or override via environment variables (CLAUDE_* prefix).
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ── Input locations ───────────────────────────────────────────────────────────
INPUTS_DIR = REPO_ROOT / "inputs"
GOOGLEVISION_DIR = REPO_ROOT / "ocr_eval" / "googlevision_output"
DMR_DB_PATH = (
    REPO_ROOT / "database" / "dmr.db"
)  # produced by scripts/import_dmr_brands.py

# ── Output locations ──────────────────────────────────────────────────────────
MODULE_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = MODULE_ROOT / "output"
RUNS_DB_PATH = MODULE_ROOT / "runs.db"
PROMPTS_DIR = MODULE_ROOT / "prompts"

# ── Models ────────────────────────────────────────────────────────────────────
# Defaults: Sonnet 4.6 for pass 1 (image+OCR per-page batch), Opus 4.7 for
# pass 2 (cross-page reasoning). Override via env if a more specific dated
# model ID is required (e.g. ``claude-sonnet-4-6-20251022``).
PASS1_MODEL = os.getenv("CLAUDE_PASS1_MODEL", "claude-sonnet-4-6")
PASS2_MODEL = os.getenv("CLAUDE_PASS2_MODEL", "claude-opus-4-7")

# ── API ───────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Pass 2 chunking: split output by page-ranges when input or output overflows.
PASS2_MAX_PAGES_PER_CHUNK = int(os.getenv("CLAUDE_PASS2_CHUNK_SIZE", "200"))

# Image format on disk.
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
