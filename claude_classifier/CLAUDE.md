# claude_classifier — Claude Working Guide

This file is the agent-facing companion to [README.md](./README.md) (user-facing)
and [ARCHITECTURE.md](./ARCHITECTURE.md) (design). Read those first if you need
the bigger picture.

## What this module is

A self-contained two-pass page classifier built on the Anthropic API. Lives
alongside (but is independent of) the open-source pipeline in `open_src/`. No
imports from `open_src.src.*` are permitted — everything this module needs is
inside `claude_classifier/`.

## Coding rules

1. **Self-containment** — every script `claude_classifier` uses lives inside
   `claude_classifier/`. Do not reach into `open_src/src/*` for utilities.
   Adding a dependency on another in-repo module requires explicit discussion.
2. **JSON on disk is the source of truth.** `runs.db` mirrors orchestration
   state only; a SQLite failure must never abort a run (wrap writes in
   `try/except` and log).
3. **Pass-1 outputs are immutable after `collect()`** — pass 2 reads them but
   never mutates them. Re-running pass 2 creates a new `pass2_runs/<ts>/`
   directory.
4. **Tool-use schema is the contract.** `PASS1_TOOL` / `PASS2_TOOL` define the
   shape of model output. Don't add a field to the JSON without updating the
   schema; don't add to the schema without updating downstream consumers
   (`compact_summary()`, the merge loop in `pass2.run()`, `output_schema.json`
   in the docs).
5. **The system prompts are policy, not facts.** Cross-page facts (other
   pages' summaries, masthead OCR, publication metadata) belong in the user
   message, not in the system prompt. If pass 2 needs more information, add a
   field to `compact_summary()` first.
6. **DMR matcher is deterministic.** Specificity tie-break is "lowest numeric
   entity_id wins". Don't add non-deterministic dedup logic.
7. **Costs are recorded on every API call.** Both passes must populate the
   `runs.db` cost columns AND the corresponding `run_metadata.json` block.
   If you add a new pass or new model call, add cost tracking before merging.
8. **`page_label` / `printed_page_number` is TEXT.** Magazines use roman
   numerals and prefixed page numbers (`A12`, `xiv`). Never cast to int.
9. **`brands.canonical` is the matcher's raw output.** It is intentionally
   unfiltered; downstream consumers must apply their own quality heuristics.
   Don't introduce silent filtering inside the matcher or `reconcile.py`.
10. **No content-policy interpretation in code.** All editorial / advertorial
    / monography rules live in `prompts/pass2_system.md`. Code arranges the
    inputs; the model applies the rules.

## File-by-file responsibilities

| File | What belongs here | What does **not** belong here |
|---|---|---|
| `cli.py` | argparse wiring only | business logic, side effects beyond dispatch |
| `config.py` | static defaults + env overrides | function definitions |
| `schemas.py` | Anthropic tool input schemas | runtime data shapes (those are in `dataclasses`) |
| `pass1.py` | batch submission, polling, per-page write | cross-page reasoning |
| `pass2.py` | cross-page revision orchestration | per-page schema definitions |
| `reconcile.py` | OCR text → canonical brand list (thin wrapper) | matcher internals |
| `dmr_matcher.py` | Aho-Corasick automaton + normalisation | publication-specific logic |
| `pricing.py` | per-model rates + cost computation | model selection |
| `db.py` | SQLite schema + helpers | analysis content |
| `io_paths.py` | path conventions + run_id format | mutation of output files |
| `publication.py` | folder-name parsing | scraping or external lookups |
| `prompts/` | system prompts (Markdown) | tool schemas, data |

## Working with prompts

- **Iterate prompts the same way as code.** Each pass-2 attempt creates a new
  `pass2_runs/<ts>/` directory — diff `current_pass2` against a previous one
  to evaluate prompt changes.
- **Pass-1 prompt is locked.** It was validated 7/7 on a Vogue UK smoke
  subset over three iterations. Do not iterate further without a new failing
  case and a written justification.
- **Pass-2 rules trace to DMR documentation.** The Step 1 → Step 2 → Step 3
  flowchart in `pass2_system.md` mirrors the DMR editorial / advertorial
  classification rules. If you change a rule, link to the DMR rule it
  encodes.
- **Continuation-page byline lookback** — currently encoded in
  `pass2_system.md` Step 3.1. Validation pending on a full magazine run.

## Commands you'll actually use

```bash
# Submit a batch
uv run python -m claude_classifier pass1 --input inputs/<folder>

# Poll (returns non-zero while in progress — safe to script)
uv run python -m claude_classifier pass1-collect --run <run_id>

# Pass 2 (rerun freely; each run lives in its own pass2_runs/<ts>/ dir)
uv run python -m claude_classifier pass2 --run <run_id>

# All runs + cost
uv run python -m claude_classifier list

# In-module self-test for the DMR matcher
uv run python -m claude_classifier.scripts.test_reconcile
```

## Common pitfalls

- **Don't put cross-page reasoning in pass 1.** Pass 1 sees one page; cross-
  page reconciliation only makes sense after every page has been classified.
- **Don't trust `brands.claude_visual` alone.** It's Claude's visual ID; for
  canonical identity always cross-reference with `brands.canonical` (DMR
  matcher).
- **Don't trust `brands.canonical` alone either.** The matcher is noisy
  because the DMR CSV contains common English words registered as brands
  (`LOVE`, `LOVER`, `OLIVIA`, `RODRIGO`). Always cross-reference with
  `claude_visual` or apply length/specificity filters downstream.
- **Don't forget batch discount.** When computing pass-1 cost, pass
  `batch=True` to `compute_cost()`. Pass 2 is `batch=False`.
- **`current_pass2` is a symlink, not a directory.** `ls -la` to see the
  target.
- **Image-only pages are valid.** The Saint Laurent / Rampling page in the
  Vogue smoketest (`42524873`) has no OCR — pass 1 handles this by sending
  an empty OCR block and trusting the image.

## Memory & state

- All persistent state is in `output/<run_id>/` and `runs.db`. Nothing is
  written to `/tmp`, the user's home, or the repo root.
- Re-running `pass1` for the same `--input` creates a **new** `run_id` (the
  run_id includes a UTC timestamp). The old run is not touched.
- `pass1-collect` is idempotent — calling it after a batch has been collected
  re-writes the same per-page files.
- `pass2 --run <run_id>` is non-destructive — each call creates a fresh
  `pass2_runs/<ts>/` directory; the `current_pass2` symlink updates to the
  newest one.

## Things to verify before merging changes

- [ ] `uv run python -m claude_classifier.scripts.test_reconcile` still
      finds the expected canonical entities.
- [ ] `runs.db` has cost columns populated after a fresh pass-1 collect and a
      fresh pass-2 run.
- [ ] `run_metadata.json` has both `pass1.cost` and `pass2_runs.<id>.cost`
      blocks after a full run.
- [ ] Pass-2 output JSONs preserve all pass-1 fields verbatim (use a diff
      against `pass1/<image_id>.json` to confirm).
- [ ] No new imports from `open_src.src.*`.
