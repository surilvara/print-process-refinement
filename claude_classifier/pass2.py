"""Pass 2: cross-page revision via a single (chunked if necessary) Claude call.

Reads all pass-1 JSONs for a run, runs the DMR alias matcher over each page's
OCR text (Q11 option c), bundles a compact summary array + masthead-page OCR,
and asks Claude to revise ``article_type`` and ``monography`` per page.

Writes results to ``pass2_runs/<timestamp>/results/<image_id>.json`` as the
full page JSON (pass-1 verbatim + pass-2 revisions merged).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from loguru import logger

from claude_classifier import db, io_paths
from claude_classifier.config import (
    GOOGLEVISION_DIR,
    PASS2_MAX_PAGES_PER_CHUNK,
    PASS2_MODEL,
    PROMPTS_DIR,
)
from claude_classifier.pricing import (
    CostBreakdown,
    add_cost_breakdowns,
    compute_cost,
)
from claude_classifier.reconcile import extract_ocr_text, load_canonical_brands_for_text
from claude_classifier.schemas import PASS2_TOOL

# ── Bundling ──────────────────────────────────────────────────────────────────


def compact_summary(pass1_json: dict, canonical_brands: list[str]) -> dict:
    """Strip pass-1 JSON down to what pass 2 needs (see Q22 Part B)."""
    return {
        "image_id": pass1_json.get("image_id") or pass1_json.get("_image_id"),
        "seq": pass1_json["sequence_index"],
        "structural_role": pass1_json.get("structural_role"),
        "printed_page_number": pass1_json.get("printed_page_number"),
        "byline": pass1_json["byline"],
        "brands_dominant": pass1_json["brands"].get("dominant"),
        "brands_canonical": canonical_brands,
        "signals": {
            "labels_found": pass1_json["signals"]["labels_found"],
            "has_qr_or_barcode": pass1_json["signals"]["has_qr_or_barcode"],
            "magazine_x_brand_headline": pass1_json["signals"][
                "magazine_x_brand_headline"
            ],
            "contact_info_on_page": pass1_json["signals"]["contact_info_on_page"],
            "looks_like_ad": pass1_json["signals"]["layout"]["looks_like_ad"],
        },
        "article_type_initial": pass1_json["article_type"]["initial"],
        "monography_initial": {
            "present": pass1_json["monography"]["present"],
            "subject": pass1_json["monography"]["subject"],
            "subtype": pass1_json["monography"]["subtype"],
        },
    }


def collect_masthead_ocr(
    run_id: str, summaries: list[dict], publication_folder: str
) -> dict[str, str]:
    """Return ``{image_id: ocr_text}`` for pages flagged ``structural_role=masthead``.

    Only masthead pages (Q20 decision) are included as anchors.
    """
    out: dict[str, str] = {}
    for s in summaries:
        if s["structural_role"] != "masthead":
            continue
        ocr_path = GOOGLEVISION_DIR / publication_folder / f"{s['image_id']}.json"
        if ocr_path.exists():
            out[s["image_id"]] = extract_ocr_text(ocr_path)
    return out


# ── Execution ─────────────────────────────────────────────────────────────────


def _load_system_prompt() -> str:
    return (PROMPTS_DIR / "pass2_system.md").read_text()


def _chunk(seq: list, size: int) -> Iterable[list]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def run(run_id: str) -> str:
    """Execute pass 2 against a completed pass-1 run. Returns pass2_run_id."""
    from anthropic import Anthropic

    metadata = json.loads(io_paths.metadata_path(run_id).read_text())
    publication_folder = Path(metadata["input_path"]).name
    pub_ctx = metadata["publication"]

    pass1_root = io_paths.pass1_dir(run_id)
    pass1_files = sorted(pass1_root.glob("*.json"))
    if not pass1_files:
        raise ValueError(f"No pass1 results found for {run_id}")

    # Load pass-1, run alias matcher, build compact summaries.
    summaries: list[dict] = []
    full_pages: dict[str, dict] = {}
    canonical_by_image: dict[str, list[dict]] = {}
    for path in pass1_files:
        page = json.loads(path.read_text())
        if "error" in page:
            continue
        page["_image_id"] = path.stem
        full_pages[path.stem] = page
        ocr_path = GOOGLEVISION_DIR / publication_folder / f"{path.stem}.json"
        text = extract_ocr_text(ocr_path) if ocr_path.exists() else ""
        matched = load_canonical_brands_for_text(text)
        # Dedupe (name, entity_type) and sort for stable output.
        seen: set[tuple[str, str]] = set()
        canonical_objs: list[dict] = []
        for b in matched:
            key = (b.name, b.entity_type)
            if key in seen:
                continue
            seen.add(key)
            canonical_objs.append({"name": b.name, "entity_type": b.entity_type})
        canonical_objs.sort(key=lambda d: (d["name"], d["entity_type"]))
        canonical_by_image[path.stem] = canonical_objs
        canonical_names = [d["name"] for d in canonical_objs]
        summaries.append(compact_summary(page, canonical_names))

    summaries.sort(key=lambda s: s["seq"])
    anchor_ocr = collect_masthead_ocr(run_id, summaries, publication_folder)

    pass2_run_id = io_paths.utc_timestamp()
    results_dir = io_paths.pass2_run_dir(run_id, pass2_run_id)
    results_dir.mkdir(parents=True, exist_ok=True)

    with db.connect() as conn:
        db.insert_pass2_run(
            conn,
            pass2_run_id=pass2_run_id,
            run_id=run_id,
            started_at=io_paths.utc_iso(),
            model=PASS2_MODEL,
        )

    client = Anthropic()
    system_prompt = _load_system_prompt()
    revisions: dict[str, dict] = {}
    cost_items: list[CostBreakdown] = []
    chunks = list(_chunk(summaries, PASS2_MAX_PAGES_PER_CHUNK))
    logger.info(
        f"Pass 2 for {run_id}: {len(summaries)} pages in {len(chunks)} chunk(s)"
    )

    for chunk in chunks:
        chunk_ids = [s["image_id"] for s in chunk]
        user_text = json.dumps(
            {
                "publication_context": pub_ctx,
                "all_pages": summaries,  # full context every chunk
                "anchor_masthead_ocr": anchor_ocr,
                "revise_pages": chunk_ids,  # only these in this chunk
            },
            indent=2,
            ensure_ascii=False,
        )
        response = client.messages.create(
            model=PASS2_MODEL,
            max_tokens=8192,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[PASS2_TOOL],
            tool_choice={"type": "any"},  # multiple tool calls per chunk
            messages=[{"role": "user", "content": user_text}],
        )
        usage = getattr(response, "usage", None)
        if usage is not None:
            cost_items.append(compute_cost(usage, model=PASS2_MODEL, batch=False))
        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                rev = block.input
                image_id = rev.get("image_id") if isinstance(rev, dict) else None
                if not image_id:
                    logger.warning(
                        f"Pass 2 tool_use missing image_id; skipping: {rev!r}"
                    )
                    continue
                revisions[image_id] = rev

    # Merge revisions into full pass-1 pages and write final results.
    for image_id, page in full_pages.items():
        rev = revisions.get(image_id)
        if rev is not None:
            at = rev.get("article_type") if isinstance(rev, dict) else None
            if isinstance(at, dict) and "final" in at:
                page["article_type"]["final"] = at["final"]
                if "confidence" in at:
                    page["article_type"]["confidence"] = at["confidence"]
                page["article_type"]["revision_reason"] = at.get("revision_reason")
            else:
                logger.warning(
                    f"Pass 2 revision for {image_id} missing article_type; "
                    f"keeping pass-1 value"
                )
            mono = rev.get("monography") if isinstance(rev, dict) else None
            if isinstance(mono, dict):
                if "present" in mono:
                    page["monography"]["present"] = mono["present"]
                if "subject" in mono:
                    page["monography"]["subject"] = mono["subject"]
                if "subtype" in mono:
                    page["monography"]["subtype"] = mono["subtype"]
        # Surface DMR matcher output alongside Claude's visual brand list.
        page.setdefault("brands", {})["canonical"] = canonical_by_image.get(
            image_id, []
        )
        page.pop("_image_id", None)
        (results_dir / f"{image_id}.json").write_text(
            json.dumps(page, indent=2, ensure_ascii=False)
        )

    io_paths.update_current_pass2_symlink(run_id, pass2_run_id)

    total_cost = add_cost_breakdowns(cost_items)
    if total_cost is not None:
        # Per-pass2-run cost file.
        try:
            (results_dir.parent / "cost.json").write_text(
                json.dumps(total_cost.to_dict(), indent=2)
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to write pass2 cost.json: {e}")
        # Update run_metadata.json (best-effort).
        try:
            meta_path = io_paths.metadata_path(run_id)
            metadata = json.loads(meta_path.read_text())
            metadata.setdefault("pass2_runs", {})[pass2_run_id] = {
                "started_at": metadata.get("pass2_runs", {})
                .get(pass2_run_id, {})
                .get("started_at"),
                "model": PASS2_MODEL,
                "chunk_count": len(chunks),
                "cost": total_cost.to_dict(),
            }
            meta_path.write_text(json.dumps(metadata, indent=2))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to write pass2 cost to metadata: {e}")

    with db.connect() as conn:
        db.update_pass2_run_status(
            conn,
            pass2_run_id=pass2_run_id,
            status="complete",
            completed_at=io_paths.utc_iso(),
            chunk_count=len(chunks),
        )
        if total_cost is not None:
            db.update_pass2_run_cost(
                conn,
                pass2_run_id=pass2_run_id,
                input_tokens=total_cost.input_tokens,
                output_tokens=total_cost.output_tokens,
                cache_creation_input_tokens=total_cost.cache_creation_input_tokens,
                cache_read_input_tokens=total_cost.cache_read_input_tokens,
                cost_usd=total_cost.total_cost_usd,
            )

    logger.info(
        f"Pass 2 complete: {results_dir}"
        + (
            f" (cost ${total_cost.total_cost_usd:.4f})"
            if total_cost is not None
            else ""
        )
    )
    return pass2_run_id
