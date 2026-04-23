from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from src.config import PipelineConfig
from src.models.base import (
    DocumentResult,
    ImageRegionWithDetections,
    PageResult,
    TextBlockWithEntities,
)


def _serialize_page(page: PageResult) -> dict:
    return {
        "page_number": page.page_number,
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


def build_output_json(doc_result: DocumentResult, config: PipelineConfig) -> dict:
    """Build the full output JSON structure for a document."""
    now = datetime.now(timezone.utc)

    return {
        "metadata": {
            "input_file": doc_result.input_file,
            "timestamp": now.isoformat(),
            "models": config.get_model_summary(),
            "pipeline_version": "1.0.0",
        },
        "pages": [_serialize_page(p) for p in doc_result.pages],
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


def write_result(
    doc_result: DocumentResult,
    config: PipelineConfig,
    input_filename: str,
) -> Path:
    """Write a document result to a JSON file in the output directory."""
    output_dir = Path(config.output.directory)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_data = build_output_json(doc_result, config)

    # Build filename: <input_stem>_<timestamp>_<models>.json
    stem = Path(input_filename).stem
    now = datetime.now(timezone.utc)
    parts = [stem]
    if config.output.include_timestamp:
        parts.append(now.strftime("%Y-%m-%dT%H-%M-%S"))
    if config.output.include_model_names:
        parts.append(config.get_model_name_slug())
    filename = "_".join(parts) + ".json"

    output_path = output_dir / filename
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Results written to {output_path}")
    return output_path
