import anthropic
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger

from instructions import context_prompt, no_context_prompt

PROMPTS = {
    "no_context": no_context_prompt,
    "context": context_prompt,
}
from utils import (
    MODEL,
    MAX_TOKENS,
    WINDOW_SIZE,
    SUPPORTED_MEDIA_TYPES,
    build_image_content,
    calculate_cost,
    parse_usage,
    extract_text,
)

DB_PATH = Path(__file__).parent.parent / "database" / "results.db"


def build_window_content(image_files: list[Path], target_idx: int) -> list[dict]:
    total = len(image_files)
    start = max(0, target_idx - WINDOW_SIZE)
    end = min(total - 1, target_idx + WINDOW_SIZE)

    content = []
    for idx in range(start, end + 1):
        label = f"Page {idx + 1}"
        if idx == target_idx:
            label += " [CLASSIFY THIS PAGE]"
        else:
            label += " [context only]"
        content.append({"type": "text", "text": label})
        content.append(build_image_content(str(image_files[idx])))
    return content


def call_claude(
    image_files: list[Path], target_idx: int, prompt: str
) -> tuple[str, dict]:
    client = anthropic.Anthropic()

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=[
            {
                "type": "text",
                "text": prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": build_window_content(image_files, target_idx),
            }
        ],
    )

    usage = parse_usage(message.usage)
    return extract_text(message.content), usage


def run_batch(
    image_files: list[Path],
    output_dir: Path,
    run_timestamp: str,
    input_path: Path,
    prompt: str,
) -> None:
    client = anthropic.Anthropic()

    requests = [
        {
            "custom_id": image_path.stem,
            "params": {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "system": [
                    {
                        "type": "text",
                        "text": prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                "messages": [
                    {
                        "role": "user",
                        "content": build_window_content(image_files, idx),
                    }
                ],
            },
        }
        for idx, image_path in enumerate(image_files)
    ]

    logger.info(f"Submitting batch of {len(requests)} images...")
    batch = client.beta.messages.batches.create(requests=requests)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO batch (batch_id, input_folder, run_timestamp, status, output_dir, page_count) VALUES (?, ?, ?, 'submitted', ?, ?)",
            (batch.id, str(input_path), run_timestamp, str(output_dir), len(requests)),
        )

    logger.info(f"Batch submitted — ID: {batch.id}")
    logger.info(f"Run: python retrieve.py to check status and collect results")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error(
            "Usage: python api.py <folder> --prompt <no_context|context> [--batch]"
        )
        sys.exit(1)

    input_path = Path(sys.argv[1])
    use_batch = "--batch" in sys.argv

    try:
        prompt_idx = sys.argv.index("--prompt")
        prompt_key = sys.argv[prompt_idx + 1]
    except (ValueError, IndexError):
        logger.error("--prompt is required. Choose: no_context or context")
        sys.exit(1)

    if prompt_key not in PROMPTS:
        logger.error(f"Unknown prompt '{prompt_key}'. Choose: {list(PROMPTS.keys())}")
        sys.exit(1)

    selected_prompt = PROMPTS[prompt_key]
    logger.info(f"Using prompt: {prompt_key}")

    if not input_path.is_dir():
        logger.error(f"{input_path} is not a directory")
        sys.exit(1)

    image_files = sorted(
        p for p in input_path.iterdir() if p.suffix.lower() in SUPPORTED_MEDIA_TYPES
    )

    if not image_files:
        logger.error(f"No supported images found in {input_path}")
        sys.exit(1)

    run_timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    output_dir = (
        Path(__file__).parent / "responses" / f"{input_path.name}_{run_timestamp}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    if use_batch:
        run_batch(image_files, output_dir, run_timestamp, input_path, selected_prompt)
    else:
        total_input = total_output = 0

        for idx, image_path in enumerate(image_files):
            logger.info(f"Processing {image_path.name} ({idx + 1}/{len(image_files)})")
            response, usage = call_claude(image_files, idx, selected_prompt)

            total_input += usage["input_tokens"]
            total_output += usage["output_tokens"]
            logger.info(
                f"Window: pages {max(1, idx + 1 - WINDOW_SIZE)}-{min(len(image_files), idx + 1 + WINDOW_SIZE)} "
                f"| input: {usage['input_tokens']}, "
                f"cache write: {usage['cache_creation_input_tokens']}, "
                f"cache read: {usage['cache_read_input_tokens']}, "
                f"output: {usage['output_tokens']}, cost: ${usage['cost_usd']:.6f}"
            )

            output_file = output_dir / f"{image_path.stem}.json"
            payload = {
                "image": str(image_path),
                "window": {
                    "start": max(1, idx + 1 - WINDOW_SIZE),
                    "end": min(len(image_files), idx + 1 + WINDOW_SIZE),
                },
                "prompt": prompt_key,
                "model": MODEL,
                "response": response,
                "usage": usage,
                "timestamp": run_timestamp,
            }
            output_file.write_text(json.dumps(payload, indent=2))
            logger.info(f"Saved to {output_file}")

        total_cost = calculate_cost(
            {"input_tokens": total_input, "output_tokens": total_output}
        )
        logger.info(
            f"Total — input: {total_input}, output: {total_output}, cost: ${total_cost:.6f}"
        )
