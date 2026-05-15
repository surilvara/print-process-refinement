# Session — 2026-05-06: SQLite mirror, publications, page classification

## What we set out to do

The pipeline already wrote per-image JSON files. Goals for the session:
1. Add a queryable mirror so we don't have to grep the filesystem for cross-run analysis.
2. Treat a folder of images as a single **publication** so we can run publication-level analysis (brands across an issue, etc.).
3. Label each page **editorial** or **advertising**.
4. Modularise the publication metadata extraction so the parsing rule is swappable.

## What we built

### 1. SQLite mirror of the JSON output

Path: `database/results.db` (gitignored). The JSON file remains the source of truth; the DB is best-effort — write failures log a warning, the run never aborts.

8 tables: `publications`, `runs`, `run_errors`, `pages`, `text_blocks`, `entities`, `image_regions`, `detections`. Normalised, FK cascades.

Engineering decisions captured here so future-us doesn't relitigate:
- **No `raw_json` column.** Doubles size for no query benefit. `runs.output_json_filename` (basename) plus `output.directory` is enough to find the full payload.
- **Normalized over JSON column.** The whole point is queries like "top brands across all magazines processed with model X" — a JSON-blob column would just be a slower filesystem.
- **Append per run.** Re-running creates a new `runs` row; UNIQUE on `output_json_filename` only catches accidental replays.
- **`ON DELETE CASCADE`** down the run → pages → text_blocks → entities chain. `ON DELETE SET NULL` on `runs.publication_id` (loose runs are first-class).
- **BBoxes stored as four `REAL` columns**, not JSON, so spatial filters are indexable.

### 2. Publication tracking

A subdirectory of the input root becomes a publication; loose top-level files stay standalone. Each page-image still produces its own JSON + `runs` row, all linked via `publication_id`.

- **Identity = folder basename** (UNIQUE). Re-running the same folder reuses the row; multiple issues of the same magazine each get their own row.
- **`page_label` is TEXT, not INTEGER.** Newspapers/magazines use `iv`, `A12`, `B3`. TEXT means no schema change when those land. `runs.id` ASC preserves input order.
- **Subdirectories of the input root are publications; the input root itself is never one.** Predictable rule that preserves existing flat-batch behaviour.
- **`processed/` preserves folder hierarchy** — `inputs/Vogue/p1.jpg` → `processed/Vogue/p1.jpg`. Empty publication folders are auto-cleaned; the input root is never touched.

### 3. Folder name parser

Convention: `<magazine>_<YYYY-MM-DD>` or `<magazine>_<YYYY-MM>`. Magazine name keeps internal underscores (`Vogue_Italia_2026-04-15` → `Vogue_Italia`). Non-matching folders process anyway with `magazine_name = basename`, `issue_date = NULL`, plus a warning. Folder basename remains the UNIQUE identity regardless of parse outcome.

### 4. Pluggable extractor pattern

Modularised the parser as `PublicationMetadataExtractor` (ABC) in `src/publication.py` with a `PUBLICATION_EXTRACTORS` registry, picked by `config.yaml.publication_extraction.backend`. Default = `FolderNameRegexExtractor`. Future implementations (sidecar `publication.yaml`, LLM-driven, ISSN database) drop in without touching `input_handler` or `pipeline`.

### 5. Page classification — editorial vs advertising

Heuristic at JSON-serialization time using signals already produced upstream:

A page is `advertising` if **either**
- `≥ advertisement_block_ratio` of text blocks are `advertisement_copy` (from layout), **or**
- any image region has a detection in `advertisement_detection_labels` at `confidence ≥ advertisement_detection_confidence`.

All thresholds tunable in `config.yaml.page_classification`. Stored as `pages.classification` (any string accepted) plus `pages.classification_reason` (which signal fired). The DB column accepts any string, so a real classifier (CLIP-based, fine-tuned, etc.) can replace the heuristic later with no schema change.

### 6. Idempotent migration strategy

Schema bumps auto-upgrade existing DBs via `ALTER TABLE ADD COLUMN`. Critical detail discovered the hard way: **migration must run before `executescript(SCHEMA)`** because the schema's `CREATE INDEX` statements reference new columns. First implementation got this wrong; smoke-test caught it.

## SQL queries written

- **`scripts/publication_analysis.sql`** — publication-level summary (pages, editorial/advertising split, distinct/total brands, products, persons). Uses a `latest_run_per_page` CTE to collapse re-runs to the most recent. Verified against real DB.
- **Single-page entity dump** — two variants: by `publication_name + page_label` (human-friendly) or by `run_id` directly.

## Observations on real data (vogue_uk_2026-04-01)

255 pages processed. The publication-level analysis on real data surfaced two quality issues worth addressing next session:

- **All 255 pages classified `editorial`.** The heuristic isn't firing as `advertising`. Likely (a) PaddleOCR-VL doesn't emit `advertisement_copy` as a `block_type`, or (b) OWLv2 detections are below the 0.5 confidence threshold on this content. Diagnose with:
  ```sql
  SELECT DISTINCT block_type FROM text_blocks;
  SELECT label, COUNT(*) FROM detections GROUP BY label ORDER BY 2 DESC;
  ```
- **1026 "distinct brands" is inflated by NER noise.** `en_core_web_trf` over-tags ALL-CAPS masthead text (`GLOBAL CONTENT BUSINESS OPERATIONS`, `LATIN AMERICA`) and uppercase real names (`CHARLOTTE RUTTER`) as `ORG → BRAND`. **971 distinct persons** has the mirror problem (`RALPH LAUREN` tagged `PERSON`). Quality issue, not a query issue. Options: try `en_core_web_lg`, post-filter against a brand/celebrity reference list, or normalise OCR to lower-case before NER.

## Deferred items

- **Celebrity detection** — explicitly punted. Stand-in: count `PERSON` entities in the publication summary.
- **`publication.yaml` sidecar metadata** — `publications.{language, notes}` exist as nullable columns so this can land later without migration.
- **Real page classifier** — heuristic in place; column type allows drop-in replacement.

## Open questions for next session

1. Diagnose why no pages classify as `advertising` (queries above).
2. Address NER over-tagging on uppercase text.
3. The `dmr-print-analysis` skill was installed mid-session and will load on the next Claude Code start. Its scope (editorial classification, advertorials, fashion/beauty methodology, product categorization) overlaps directly with this work — it's worth consulting before deciding on a real classifier or refining the heuristic thresholds.

## Files changed in this session

**New:**
- `src/db.py` — SQLite schema + best-effort `insert_run` + idempotent migration
- `src/publication.py` — `PublicationMetadataExtractor` ABC + registry + default impl
- `scripts/publication_analysis.sql`
- `database/results.db` — auto-generated on first pipeline run after the changes

**Modified:**
- `src/input_handler.py` — `InputItem` + `PublicationInfo` types, recursive walk for publications
- `src/output_handler.py` — `classify_page`, publication block in metadata, DB hook
- `src/pipeline.py` — extractor wiring, processed/ folder-hierarchy preservation
- `src/config.py`, `config.yaml` — `DatabaseConfig`, `PublicationExtractionConfig`, `PageClassificationConfig`
- `output_schema.json` — `metadata.publication`, `pages[].classification`, `pages[].classification_reason`
- `.gitignore` — `database/`
- `SPEC.md`, `SUMMARY.md` — updated throughout

## Note on this file's location

Saved to `session/` per request. If you adopt a more standard layout later, `docs/sessions/<YYYY-MM-DD>-<slug>.md` keeps session journals next to `SPEC.md`/`SUMMARY.md`. For decision-focused records (one file per decision, structured Context → Decision → Consequences), the convention is ADRs at `docs/decisions/NNNN-<slug>.md`.
