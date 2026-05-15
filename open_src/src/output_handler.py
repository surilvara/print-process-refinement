from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from src.config import PageClassificationConfig, PipelineConfig
from src.db import insert_run
from src.models.base import (
    DocumentResult,
    ImageRegionWithDetections,
    PageResult,
    TextBlockWithEntities,
)


def classify_page(
    page: PageResult,
    config: PageClassificationConfig,
    publication_name: str | None = None,
) -> tuple[str, str]:
    """Classify a single page as 'editorial', 'advertising', or 'advertorial'.

    Decision order (first match wins):
      1. PR keyword found in any text block
           → 'advertorial', UNLESS the publication is a Japan/Korea title AND
             the page has a byline block (editorial credits present) — in which
             case the label is overridden and the page is 'editorial'.
      2. High advertisement_copy block ratio OR OWLv2 advertisement detection
           → 'advertising'
      3. Default → 'editorial'

    Japan/Korea structural override (§6, general-rules.md): publishers in those
    markets use 'Sponsored' / 'In Collaboration With' on legitimate editorial
    pages. Presence of a byline block (redattore/fotografo credit) is the
    key structural signal that the page is editorial despite the label.
    """
    all_text = " ".join(tb.text for tb in page.text_blocks).lower()
    has_byline = any(tb.block_type == "byline" for tb in page.text_blocks)

    # ── Step 1: PR keyword scan ──────────────────────────────────────────────
    matched_keyword: str | None = None
    for kw in config.pr_keywords:
        if kw.lower() in all_text:
            matched_keyword = kw
            break

    if matched_keyword is not None:
        # Japan/Korea structural override: if this is a known Japan/Korea
        # publication AND the page has editorial credits (byline), the PR
        # label alone is insufficient — treat as editorial.
        is_japan_korea = False
        if publication_name:
            pub_lower = publication_name.lower()
            is_japan_korea = any(
                kw.lower() in pub_lower for kw in config.japan_korea_publisher_keywords
            )

        if is_japan_korea and has_byline:
            return (
                "editorial",
                f"PR keyword '{matched_keyword}' found but overridden: "
                "Japan/Korea publication with editorial byline credits present",
            )

        return (
            "advertorial",
            f"PR keyword '{matched_keyword}' found in text block"
            + (
                f" (Japan/Korea publication '{publication_name}' "
                "but no byline — treated as advertorial)"
                if is_japan_korea
                else ""
            ),
        )

    # ── Step 2: Pure ADV signals ─────────────────────────────────────────────
    n_blocks = len(page.text_blocks)
    n_ad_blocks = sum(
        1 for tb in page.text_blocks if tb.block_type == "advertisement_copy"
    )
    block_ratio = n_ad_blocks / n_blocks if n_blocks else 0.0

    matching_detection: tuple[str, float] | None = None
    ad_labels = set(config.advertisement_detection_labels)
    for ir in page.image_regions:
        for d in ir.detections:
            if (
                d.label in ad_labels
                and d.confidence >= config.advertisement_detection_confidence
            ):
                matching_detection = (d.label, d.confidence)
                break
        if matching_detection is not None:
            break

    block_threshold_met = block_ratio >= config.advertisement_block_ratio
    if block_threshold_met or matching_detection is not None:
        reasons = []
        if block_threshold_met:
            reasons.append(
                f"advertisement_copy ratio {block_ratio:.2f} ≥ "
                f"{config.advertisement_block_ratio:.2f}"
            )
        if matching_detection is not None:
            label, conf = matching_detection
            reasons.append(f"detection '{label}' confidence {conf:.2f}")
        return "advertising", "; ".join(reasons)

    # ── Step 3: Default ──────────────────────────────────────────────────────
    if n_blocks == 0 and not page.image_regions:
        return "editorial", "no signals (default)"
    return (
        "editorial",
        f"no PR keywords; advertisement_copy ratio {block_ratio:.2f} < "
        f"{config.advertisement_block_ratio:.2f}; no qualifying detections",
    )


def _serialize_page(
    page: PageResult,
    config: PageClassificationConfig,
    publication_name: str | None = None,
) -> dict:
    classification, reason = classify_page(page, config, publication_name)
    return {
        "page_number": page.page_number,
        "classification": classification,
        "classification_reason": reason,
        "text_blocks": [
            {
                "id": tb.id,
                "type": tb.block_type,
                "text": tb.text,
                "bbox": tb.bbox.to_list(),
                "entities": [
                    {
                        "text": e.text,
                        "label": e.label,
                        "start": e.start,
                        "end": e.end,
                    }
                    for e in tb.entities
                ],
            }
            for tb in page.text_blocks
        ],
        "image_regions": [
            {
                "id": ir.id,
                "bbox": ir.bbox.to_list(),
                "detections": [
                    {
                        "label": d.label,
                        "confidence": d.confidence,
                        "bbox": d.bbox.to_list(),
                    }
                    for d in ir.detections
                ],
            }
            for ir in page.image_regions
        ],
    }


def _build_document_summary(pages: list[PageResult]) -> dict:
    """Aggregate entities and detections across all pages."""
    entity_counter: Counter = Counter()
    detection_counter: Counter = Counter()

    for page in pages:
        for tb in page.text_blocks:
            for e in tb.entities:
                entity_counter[(e.text, e.label)] += 1
        for ir in page.image_regions:
            for d in ir.detections:
                detection_counter[d.label] += 1

    all_entities = [
        {"text": text, "label": label, "count": count}
        for (text, label), count in entity_counter.most_common()
    ]
    all_detections = dict(detection_counter.most_common())

    return {
        "all_entities": all_entities,
        "all_detections_summary": all_detections,
        "total_pages": len(pages),
    }


def build_output_json(
    doc_result: DocumentResult,
    config: PipelineConfig,
    publication_meta: dict | None = None,
) -> dict:
    """Build the full output JSON structure for a document.

    `publication_meta`, when provided, is embedded under metadata.publication
    so the JSON file is self-describing (no DB lookup needed). Shape:
        {"name": str, "source_path": str, "page_label": str, "total_pages": int}
    """
    now = datetime.now(timezone.utc)

    metadata: dict = {
        "input_file": doc_result.input_file,
        "timestamp": now.isoformat(),
        "models": config.get_model_summary(),
        "pipeline_version": "1.0.0",
    }
    if publication_meta is not None:
        metadata["publication"] = publication_meta

    pub_name: str | None = None
    if publication_meta:
        pub_name = publication_meta.get("magazine_name") or publication_meta.get("name")

    return {
        "metadata": metadata,
        "pages": [
            _serialize_page(p, config.page_classification, pub_name)
            for p in doc_result.pages
        ],
        "document": _build_document_summary(doc_result.pages),
        "errors": doc_result.errors,
    }


def generate_output_filename(config: PipelineConfig) -> str:
    """Generate a filename following the naming convention."""
    parts = []
    now = datetime.now(timezone.utc)

    if config.output.include_timestamp:
        parts.append(now.strftime("%Y-%m-%dT%H-%M-%S"))
    if config.output.include_model_names:
        parts.append(config.get_model_name_slug())

    return "_".join(parts) + ".json" if parts else "result.json"


def build_run_subdir_name(
    run_timestamp: str,
    publication_meta: dict | None,
    input_filename: str,
) -> str:
    """Build the per-run subdirectory name used to group outputs.

    Pattern mirrors api/responses: ``<publication_name_or_input_stem>_<timestamp>``.
    """
    if publication_meta and publication_meta.get("name"):
        prefix = publication_meta["name"]
    else:
        prefix = Path(input_filename).stem
    return f"{prefix}_{run_timestamp}"


def write_result(
    doc_result: DocumentResult,
    config: PipelineConfig,
    input_filename: str,
    publication_meta: dict | None = None,
    run_timestamp: str | None = None,
) -> Path:
    """Write a document result to a JSON file under a per-run subdirectory.

    Layout:
        <output.directory>/<publication_or_stem>_<run_timestamp>/<input_stem>.json
    """
    if run_timestamp is None:
        run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    subdir_name = build_run_subdir_name(run_timestamp, publication_meta, input_filename)
    output_dir = Path(config.output.directory) / subdir_name
    output_dir.mkdir(parents=True, exist_ok=True)

    output_data = build_output_json(
        doc_result, config, publication_meta=publication_meta
    )

    filename = f"{Path(input_filename).stem}.json"
    output_path = output_dir / filename
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Results written to {output_path}")

    if config.database.enabled:
        # Store the path relative to the output root so the UNIQUE constraint
        # holds across runs (same page-stem can recur in different run folders).
        db_filename = f"{subdir_name}/{filename}"
        run_id = insert_run(Path(config.database.path), output_data, db_filename)
        if run_id is not None:
            logger.info(f"Result recorded in {config.database.path} (run_id={run_id})")

    return output_path
