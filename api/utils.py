import base64
from pathlib import Path

# ── Model config ──────────────────────────────────────────────────────────────
MODEL = "claude-opus-4-7"
MAX_TOKENS = 1500  # output tokens limit
WINDOW_SIZE = 7  # pages before and after target page (sliding window)

# ── Pricing per million tokens (claude-opus-4-7) ──────────────────────────────
INPUT_COST_PER_M = 5.00
CACHE_WRITE_COST_PER_M = 6.25
CACHE_READ_COST_PER_M = 0.50
OUTPUT_COST_PER_M = 25.00
BATCH_DISCOUNT = 0.5  # Batch API gives 50% off all token costs

# ── Supported image types ─────────────────────────────────────────────────────
SUPPORTED_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def encode_image(image_path: str) -> tuple[str, str]:
    """Return (base64_data, media_type) for a local image file."""
    path = Path(image_path)
    media_type = SUPPORTED_MEDIA_TYPES.get(path.suffix.lower())
    if not media_type:
        raise ValueError(
            f"Unsupported image type: {path.suffix}. Must be one of {list(SUPPORTED_MEDIA_TYPES)}"
        )
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, media_type


def build_image_content(image_path: str) -> dict:
    data, media_type = encode_image(image_path)
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }


def calculate_cost(usage: dict, batch: bool = False) -> float:
    discount = BATCH_DISCOUNT if batch else 1.0
    return round(
        (
            usage.get("cache_creation_input_tokens", 0)
            / 1_000_000
            * CACHE_WRITE_COST_PER_M
            + usage.get("cache_read_input_tokens", 0)
            / 1_000_000
            * CACHE_READ_COST_PER_M
            + usage.get("input_tokens", 0) / 1_000_000 * INPUT_COST_PER_M
            + usage.get("output_tokens", 0) / 1_000_000 * OUTPUT_COST_PER_M
        )
        * discount,
        6,
    )


def parse_usage(msg_usage, batch: bool = False) -> dict:
    raw = {
        "input_tokens": msg_usage.input_tokens,
        "output_tokens": msg_usage.output_tokens,
        "cache_creation_input_tokens": getattr(
            msg_usage, "cache_creation_input_tokens", 0
        ),
        "cache_read_input_tokens": getattr(msg_usage, "cache_read_input_tokens", 0),
    }
    raw["total_tokens"] = raw["input_tokens"] + raw["output_tokens"]
    raw["cost_usd"] = calculate_cost(raw, batch=batch)
    return raw


def extract_text(content) -> str:
    """Safely extract text from message content blocks."""
    return next(b.text for b in content if hasattr(b, "text"))
