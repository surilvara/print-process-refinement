"""Load Google Vision JSON responses into the normalised OcrOutput schema.

Google Vision returns:
- `textAnnotations[0]` — full page text + page bbox.
- `textAnnotations[1:]` — per-word, with bbox.
- `fullTextAnnotation` — structured pages → blocks → paragraphs → words → symbols.

We use `fullTextAnnotation` because it gives paragraph-level grouping that is
roughly comparable to the text blocks emitted by layout-aware OCR models.

Each paragraph becomes one OcrBlock. Text is reconstructed from the symbols
respecting `detectedBreak` (SPACE, SURE_SPACE, EOL_SURE_SPACE, LINE_BREAK).
"""

from __future__ import annotations

import json
from pathlib import Path

from schema import BBox, OcrBlock, OcrOutput

# Google Vision detectedBreak types → trailing character to append.
# https://cloud.google.com/vision/docs/reference/rest/v1/images/annotate#TextAnnotation
_BREAK_TO_CHAR = {
    "SPACE": " ",
    "SURE_SPACE": " ",
    "EOL_SURE_SPACE": " ",
    "HYPHEN": "-",
    "LINE_BREAK": "\n",
}


def _symbol_text(symbol: dict) -> str:
    """Return a symbol's text with its trailing break character appended."""
    txt = symbol.get("text", "")
    prop = symbol.get("property") or {}
    brk = (prop.get("detectedBreak") or {}).get("type")
    return txt + _BREAK_TO_CHAR.get(brk, "")


def _paragraph_text(paragraph: dict) -> str:
    parts: list[str] = []
    for word in paragraph.get("words", []):
        for symbol in word.get("symbols", []):
            parts.append(_symbol_text(symbol))
    return "".join(parts).strip()


def _paragraph_confidence(paragraph: dict) -> float:
    confs: list[float] = []
    for word in paragraph.get("words", []):
        for symbol in word.get("symbols", []):
            c = symbol.get("confidence")
            if c is not None:
                confs.append(float(c))
    return round(sum(confs) / len(confs), 4) if confs else 0.0


def load_gvision(path: Path) -> OcrOutput:
    """Parse a Google Vision JSON file into normalised OcrOutput.

    Accepts both shapes the API can produce:
    - list of {"responses": [...]}  (batch / async output)
    - dict {"responses": [...]}     (single image annotate)
    """
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, list):
        raw = raw[0]
    response = raw["responses"][0]
    full = response.get("fullTextAnnotation") or {}
    pages = full.get("pages") or []
    if not pages:
        return OcrOutput(
            image_stem=path.stem,
            image_width=0,
            image_height=0,
            runner="google_vision",
            full_text=full.get("text", ""),
            blocks=[],
        )

    # Vision returns one entry per image; we assume single-image inputs.
    page = pages[0]
    img_w = int(page.get("width", 0))
    img_h = int(page.get("height", 0))

    blocks: list[OcrBlock] = []
    for block in page.get("blocks", []):
        for paragraph in block.get("paragraphs", []):
            text = _paragraph_text(paragraph)
            if not text:
                continue
            bbox_data = paragraph.get("boundingBox", {})
            vertices = bbox_data.get("vertices", []) or bbox_data.get(
                "normalizedVertices", []
            )
            bbox = BBox.from_vertices(vertices, img_w, img_h)
            blocks.append(
                OcrBlock(
                    text=text,
                    bbox=bbox,
                    confidence=_paragraph_confidence(paragraph),
                    block_type="unknown",  # Vision doesn't classify
                )
            )

    return OcrOutput(
        image_stem=path.stem,
        image_width=img_w,
        image_height=img_h,
        runner="google_vision",
        full_text=full.get("text", "").strip(),
        blocks=blocks,
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python gvision_loader.py <gv.json>")
        sys.exit(1)
    out = load_gvision(Path(sys.argv[1]))
    print(
        f"{out.image_stem}: {out.image_width}x{out.image_height}, "
        f"{len(out.blocks)} blocks, {len(out.full_text)} chars"
    )
