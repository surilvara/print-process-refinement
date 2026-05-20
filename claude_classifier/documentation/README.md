# claude_classifier

Two-pass Claude-based magazine page classification.

Classifies every page in a scanned magazine with:

- `article_type` ∈ {editorial, advertising, advertorial}
- `celebrity` — present + candidate names
- `bridal` — present + evidence
- `monography` — present + subject + subtype ∈ {product, corporate, testimonial}
- `brands.claude_visual` — Claude's visual brand identification
- `brands.canonical` — DMR-matched canonical brand entities

For working rules and design decisions see [CLAUDE.md](./CLAUDE.md). For the
architecture see [ARCHITECTURE.md](./ARCHITECTURE.md).

## Quick start

```bash
# 0. Build the DMR SQLite from CSV (one-off)
uv run python scripts/import_dmr_brands.py --csv dmr_monitored_brands.csv \
    --db database/dmr.db

# 1. Submit pass 1 batch — returns run_id; exits immediately
uv run python -m claude_classifier pass1 --input inputs/vogue_uk_2026-04-01

# 2. Poll until complete (exit 0 = collected, non-zero = still in progress)
uv run python -m claude_classifier pass1-collect --run <run_id>

# 3. Run pass 2 (creates a fresh pass2_runs/<ts>/)
uv run python -m claude_classifier pass2 --run <run_id>

# 4. List runs with cost totals
uv run python -m claude_classifier list
```

## Inputs

| Path | Purpose |
|---|---|
| `inputs/<folder>/*.jpg` | Page scans (sorted alphabetically = page order) |
| `ocr_eval/googlevision_output/<folder>/<image_id>.json` | GoogleVision OCR per page |
| `database/dmr.db` | DMR monitored-brand aliases (Aho-Corasick) |

Folder naming: `<publication>_<country>_<YYYY-MM-DD>[_<suffix>]` — parsed by
[publication.py](./publication.py). Mismatches still process; metadata fields
fall back to null.

## Outputs

```
claude_classifier/output/<run_id>/
├── pass1/<image_id>.json              one file per page (pass-1 verdict)
├── pass2_runs/<timestamp>/
│   ├── results/<image_id>.json        pass-1 + pass-2 revisions merged
│   └── cost.json                      Opus token usage and USD breakdown
├── current_pass2 ── symlink ────►     pass2_runs/<latest>
└── run_metadata.json                  publication context + pass-1/2 cost
```

Costs (tokens + USD) are also mirrored into `runs.db` so `list` can show them.

## Configuration

| Env var | Default |
|---|---|
| `ANTHROPIC_API_KEY` | _required_ |
| `CLAUDE_PASS1_MODEL` | `claude-sonnet-4-6` |
| `CLAUDE_PASS2_MODEL` | `claude-opus-4-7` |
| `CLAUDE_PASS2_CHUNK_SIZE` | `200` (pages per pass-2 chunk) |

Pricing per model is in [pricing.py](./pricing.py). Batch API (pass 1)
automatically applies the 50% discount; pass 2 uses the standard rate.

## Module layout

| File | Role |
|---|---|
| [cli.py](./cli.py) | argparse subcommand dispatcher |
| [config.py](./config.py) | Paths, model IDs, env overrides |
| [schemas.py](./schemas.py) | `PASS1_TOOL` / `PASS2_TOOL` Anthropic input schemas |
| [pass1.py](./pass1.py) | Submit + collect Anthropic batch |
| [pass2.py](./pass2.py) | Cross-page revision (single / chunked) |
| [reconcile.py](./reconcile.py) | DMR matcher wrapper (OCR → canonical brands) |
| [dmr_matcher.py](./dmr_matcher.py) | Self-contained Aho-Corasick matcher |
| [pricing.py](./pricing.py) | Per-model rates + cost computation |
| [db.py](./db.py) | SQLite tracking (`runs.db`) |
| [io_paths.py](./io_paths.py) | run_id + on-disk path helpers |
| [publication.py](./publication.py) | Folder-name → publication metadata |
| [prompts/pass1_system.md](./prompts/pass1_system.md) | Pass-1 instruction policy |
| [prompts/pass2_system.md](./prompts/pass2_system.md) | Pass-2 DMR flowchart |
| [scripts/](./scripts) | In-module test/utility scripts |
