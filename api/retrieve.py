"""
retrieve.py — Check submitted batches and save results for completed ones.

Usage:
    python retrieve.py          # process all submitted batches
    python retrieve.py --list   # list all batches and their status
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from loguru import logger

from utils import calculate_cost, parse_usage, extract_text, MODEL

DB_PATH = Path(__file__).parent.parent / "database" / "results.db"


def list_batches() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT batch_id, input_folder, run_timestamp, status, page_count, total_cost_usd FROM batch ORDER BY created_at DESC"
        ).fetchall()

    if not rows:
        logger.info("No batches found.")
        return

    for (
        batch_id,
        input_folder,
        run_timestamp,
        status,
        page_count,
        total_cost_usd,
    ) in rows:
        cost_str = f"${total_cost_usd:.6f}" if total_cost_usd is not None else "pending"
        pages_str = str(page_count) if page_count is not None else "?"
        logger.info(
            f"[{status:>10}] {batch_id} | {pages_str} pages | {cost_str} | {input_folder} | {run_timestamp}"
        )


def retrieve_batch(client: anthropic.Anthropic, row: tuple) -> None:
    batch_id, input_folder, run_timestamp, _, output_dir = row
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    batch = client.beta.messages.batches.retrieve(batch_id)

    if batch.processing_status != "ended":
        logger.info(
            f"[{batch_id}] still processing — "
            f"{batch.request_counts.succeeded} succeeded, "
            f"{batch.request_counts.processing} processing"
        )
        return

    logger.info(f"[{batch_id}] completed — collecting results...")

    total_input = total_output = total_cache_write = total_cache_read = 0

    for result in client.beta.messages.batches.results(batch_id):
        if result.result.type != "succeeded":
            logger.warning(f"  {result.custom_id} failed — {result.result}")
            continue

        msg = result.result.message
        usage = parse_usage(msg.usage, batch=True)

        total_input += usage["input_tokens"]
        total_output += usage["output_tokens"]
        total_cache_write += usage["cache_creation_input_tokens"]
        total_cache_read += usage["cache_read_input_tokens"]

        payload = {
            "image": result.custom_id,
            "model": MODEL,
            "response": extract_text(msg.content),
            "usage": usage,
            "timestamp": run_timestamp,
            "batch_id": batch_id,
        }
        output_file = output_dir / f"{result.custom_id}.json"
        output_file.write_text(json.dumps(payload, indent=2))
        logger.info(f"  Saved {result.custom_id}.json — cost: ${usage['cost_usd']:.6f}")

    total_usage = {
        "input_tokens": total_input,
        "output_tokens": total_output,
        "cache_creation_input_tokens": total_cache_write,
        "cache_read_input_tokens": total_cache_read,
    }
    total_cost = calculate_cost(total_usage, batch=True)
    completed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """UPDATE batch SET
                status = 'completed',
                total_input_tokens = ?,
                total_output_tokens = ?,
                total_cache_write_tokens = ?,
                total_cache_read_tokens = ?,
                total_cost_usd = ?,
                completed_at = ?
            WHERE batch_id = ?""",
            (
                total_input,
                total_output,
                total_cache_write,
                total_cache_read,
                total_cost,
                completed_at,
                batch_id,
            ),
        )

    logger.info(
        f"  Total — input: {total_input}, output: {total_output}, "
        f"cache writes: {total_cache_write}, cache reads: {total_cache_read}, "
        f"cost: ${total_cost:.6f}"
    )


if __name__ == "__main__":
    if "--list" in sys.argv:
        list_batches()
        sys.exit(0)

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT batch_id, input_folder, run_timestamp, status, output_dir FROM batch WHERE status = 'submitted'"
        ).fetchall()

    if not rows:
        logger.info("No pending batches.")
        sys.exit(0)

    client = anthropic.Anthropic()
    for row in rows:
        retrieve_batch(client, row)
