"""Pass 1: per-page batch classification via Anthropic Message Batches API.

Two operations:
  * ``submit(input_path)``  — build & submit one batch for a magazine folder.
                              Records the batch_id in runs.db, returns run_id.
  * ``collect(run_id)``     — poll the stored batch; on completion, write
                              per-page ``pass1/<image_id>.json`` files.

Anthropic SDK is required (``anthropic`` package). The batch API supports
vision inputs and tool use; we force a single tool call per request so the
response is schema-conformant.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from claude_classifier import db, io_paths, publication
from claude_classifier.config import (
    GOOGLEVISION_DIR,
    IMAGE_EXTENSIONS,
    PASS1_MODEL,
)
from claude_classifier.pricing import (
    CostBreakdown,
    add_cost_breakdowns,
    compute_cost,
)
from claude_classifier.reconcile import extract_ocr_text
from claude_classifier.schemas import PASS1_TOOL


@dataclass
class PageInput:
    image_id: str
    sequence_index: int
    image_path: Path
    ocr_json_path: Path | None


# ── Discovery ─────────────────────────────────────────────────────────────────


def discover_pages(input_path: Path) -> list[PageInput]:
    """List images in ``input_path`` (sorted) and pair each with its OCR JSON."""
    image_files = sorted(
        p for p in input_path.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS
    )
    folder = input_path.name
    pages: list[PageInput] = []
    for seq, img in enumerate(image_files, start=1):
        ocr_path = GOOGLEVISION_DIR / folder / f"{img.stem}.json"
        pages.append(
            PageInput(
                image_id=img.stem,
                sequence_index=seq,
                image_path=img,
                ocr_json_path=ocr_path if ocr_path.exists() else None,
            )
        )
    return pages


# ── Prompt assembly ───────────────────────────────────────────────────────────


def _load_system_prompt() -> str:
    from claude_classifier.config import PROMPTS_DIR

    return (PROMPTS_DIR / "pass1_system.md").read_text()


def _image_block(path: Path) -> dict:
    """Build an Anthropic ``image`` content block (base64-embedded)."""
    media_type = (
        "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    )
    data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": data,
        },
    }


def build_request_for_page(page: PageInput) -> dict:
    """Build a single ``Request`` payload for the Batches API."""
    ocr_text = extract_ocr_text(page.ocr_json_path) if page.ocr_json_path else ""
    user_content: list[dict] = [
        _image_block(page.image_path),
        {
            "type": "text",
            "text": (
                f"sequence_index: {page.sequence_index}\n"
                f"image_id: {page.image_id}\n\n"
                f"OCR text (GoogleVision):\n```\n{ocr_text}\n```\n\n"
                "Analyse this magazine page and emit one record_page_analysis "
                "tool call."
            ),
        },
    ]
    return {
        "model": PASS1_MODEL,
        "max_tokens": 2048,
        "system": [
            {
                "type": "text",
                "text": _load_system_prompt(),
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "tools": [PASS1_TOOL],
        "tool_choice": {"type": "tool", "name": PASS1_TOOL["name"]},
        "messages": [{"role": "user", "content": user_content}],
    }


# ── Submission ────────────────────────────────────────────────────────────────


def submit(input_path: Path) -> str:
    """Build & submit the batch for one magazine folder. Returns run_id."""
    from anthropic import Anthropic
    from anthropic.types.messages.batch_create_params import Request

    pages = discover_pages(input_path)
    if not pages:
        raise ValueError(f"No images found in {input_path}")

    pub = publication.parse(input_path.name)
    run_id = io_paths.build_run_id(input_path.name)
    run_root = io_paths.run_dir(run_id)
    run_root.mkdir(parents=True, exist_ok=True)
    io_paths.pass1_dir(run_id).mkdir(exist_ok=True)

    requests: list[Request] = []
    for page in pages:
        requests.append(
            Request(
                custom_id=f"page_{page.sequence_index:04d}_{page.image_id}",
                params=build_request_for_page(page),
            )
        )

    client = Anthropic()
    logger.info(f"Submitting batch of {len(requests)} pages for run {run_id}")
    batch = client.messages.batches.create(requests=requests)

    # Record metadata + DB row.
    submitted_at = io_paths.utc_iso()
    metadata = {
        "run_id": run_id,
        "input_path": str(input_path),
        "publication": pub.to_dict(),
        "pass1": {
            "submitted_at": submitted_at,
            "batch_id": batch.id,
            "model": PASS1_MODEL,
            "page_count": len(pages),
            "custom_id_map": {
                f"page_{p.sequence_index:04d}_{p.image_id}": p.image_id for p in pages
            },
            "status": "submitted",
        },
    }
    io_paths.metadata_path(run_id).write_text(json.dumps(metadata, indent=2))

    with db.connect() as conn:
        db.insert_pass1_batch(
            conn,
            run_id=run_id,
            input_path=str(input_path),
            publication_name=pub.publication_name,
            issue_date=pub.issue_date,
            country=pub.country,
            batch_id=batch.id,
            model=PASS1_MODEL,
            page_count=len(pages),
            submitted_at=submitted_at,
        )

    logger.info(f"Batch {batch.id} submitted. Poll with: pass1-collect --run {run_id}")
    return run_id


# ── Collection ────────────────────────────────────────────────────────────────


def collect(run_id: str) -> None:
    """Poll a submitted batch; on completion write per-page JSON files."""
    from anthropic import Anthropic

    with db.connect() as conn:
        row = db.get_pass1_batch(conn, run_id)
        if row is None:
            raise ValueError(f"Unknown run_id: {run_id}")
        batch_id = row["batch_id"]

    metadata = json.loads(io_paths.metadata_path(run_id).read_text())
    id_map: dict[str, str] = metadata["pass1"]["custom_id_map"]

    client = Anthropic()
    batch = client.messages.batches.retrieve(batch_id)
    logger.info(f"Batch {batch_id} status: {batch.processing_status}")

    if batch.processing_status != "ended":
        with db.connect() as conn:
            db.update_pass1_batch_status(conn, run_id=run_id, status="in_progress")
        raise SystemExit(1)  # scriptable: non-zero => still running

    pass1_root = io_paths.pass1_dir(run_id)
    pass1_root.mkdir(parents=True, exist_ok=True)

    succeeded = failed = 0
    cost_items: list[CostBreakdown] = []
    for result in client.messages.batches.results(batch_id):
        custom_id = result.custom_id
        image_id = id_map.get(custom_id)
        if image_id is None:
            logger.warning(f"Unknown custom_id in batch results: {custom_id}")
            continue

        sequence_index = int(custom_id.split("_")[1])
        if result.result.type == "succeeded":
            message = result.result.message
            # Track per-page usage; batch API gets 50% discount.
            usage = getattr(message, "usage", None)
            if usage is not None:
                cost_items.append(compute_cost(usage, model=PASS1_MODEL, batch=True))
            tool_use = next((b for b in message.content if b.type == "tool_use"), None)
            if tool_use is None:
                _write_error(pass1_root, image_id, "no tool_use block in response")
                failed += 1
                _record_page(
                    conn_status=None,
                    run_id=run_id,
                    image_id=image_id,
                    custom_request_id=custom_id,
                    seq=sequence_index,
                    ok=False,
                    err="no tool_use",
                )
                continue
            (pass1_root / f"{image_id}.json").write_text(
                json.dumps(tool_use.input, indent=2, ensure_ascii=False)
            )
            succeeded += 1
            _record_page(
                conn_status=None,
                run_id=run_id,
                image_id=image_id,
                custom_request_id=custom_id,
                seq=sequence_index,
                ok=True,
            )
        else:
            err = getattr(result.result, "error", "unknown error")
            _write_error(pass1_root, image_id, str(err))
            failed += 1
            _record_page(
                conn_status=None,
                run_id=run_id,
                image_id=image_id,
                custom_request_id=custom_id,
                seq=sequence_index,
                ok=False,
                err=str(err),
            )

    with db.connect() as conn:
        db.update_pass1_batch_status(
            conn,
            run_id=run_id,
            status="complete" if failed == 0 else "partial",
            collected_at=io_paths.utc_iso(),
            pages_succeeded=succeeded,
            pages_failed=failed,
        )
        total_cost = add_cost_breakdowns(cost_items)
        if total_cost is not None:
            db.update_pass1_batch_cost(
                conn,
                run_id=run_id,
                input_tokens=total_cost.input_tokens,
                output_tokens=total_cost.output_tokens,
                cache_creation_input_tokens=total_cost.cache_creation_input_tokens,
                cache_read_input_tokens=total_cost.cache_read_input_tokens,
                cost_usd=total_cost.total_cost_usd,
                batch_discount=True,
            )

    # Persist cost block into run_metadata.json (best-effort).
    if total_cost is not None:
        try:
            meta_path = io_paths.metadata_path(run_id)
            metadata = json.loads(meta_path.read_text())
            metadata.setdefault("pass1", {})["cost"] = total_cost.to_dict()
            meta_path.write_text(json.dumps(metadata, indent=2))
        except Exception as e:  # noqa: BLE001 — cost write must never abort run
            logger.warning(f"Failed to write pass1 cost to metadata: {e}")

    logger.info(
        f"Pass 1 collected for {run_id}: {succeeded} succeeded, {failed} failed"
        + (
            f" (cost ${total_cost.total_cost_usd:.4f})"
            if total_cost is not None
            else ""
        )
    )


def _write_error(pass1_root: Path, image_id: str, message: str) -> None:
    payload = {"error": message, "image_id": image_id}
    (pass1_root / f"{image_id}.json").write_text(json.dumps(payload, indent=2))


def _record_page(
    *,
    conn_status,  # noqa: ANN001 — placeholder; we open a fresh conn below
    run_id: str,
    image_id: str,
    custom_request_id: str,
    seq: int,
    ok: bool,
    err: str | None = None,
) -> None:
    with db.connect() as conn:
        db.insert_pass1_page_result(
            conn,
            run_id=run_id,
            image_id=image_id,
            custom_request_id=custom_request_id,
            sequence_index=seq,
            status="success" if ok else "error",
            error_message=err,
        )
