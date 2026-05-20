"""Anthropic tool-use input schemas for pass 1 and pass 2.

Both passes invoke a single tool with `tool_choice={"type": "tool", "name": ...}`
so the API guarantees a schema-conformant JSON object in the response.
"""

from __future__ import annotations

ARTICLE_TYPES = ["editorial", "advertising", "advertorial", "unknown"]
MONOGRAPHY_SUBTYPES = ["product", "corporate", "testimonial", None]
STRUCTURAL_ROLES = [
    "cover",
    "back_cover",
    "toc",
    "masthead",
    "contributors",
    "letter_from_editor",
    "addresses_page",
    "translation",
    None,
]


# ── Pass 1: per-page analysis ────────────────────────────────────────────────

PASS1_TOOL = {
    "name": "record_page_analysis",
    "description": (
        "Record the analysis of a single magazine page. Emit exactly one tool "
        "call per page with all required fields populated."
    ),
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "sequence_index",
            "ocr_text_present",
            "structural_role",
            "printed_page_number",
            "byline",
            "brands",
            "signals",
            "article_type",
            "celebrity",
            "bridal",
            "monography",
            "notes",
        ],
        "properties": {
            "sequence_index": {"type": "integer"},
            "ocr_text_present": {"type": "boolean"},
            "structural_role": {
                "type": ["string", "null"],
                "enum": STRUCTURAL_ROLES,
            },
            "printed_page_number": {"type": ["string", "null"]},
            "byline": {
                "type": "object",
                "additionalProperties": False,
                "required": ["editor", "photographer"],
                "properties": {
                    "editor": {"type": ["string", "null"]},
                    "photographer": {"type": ["string", "null"]},
                },
            },
            "brands": {
                "type": "object",
                "additionalProperties": False,
                "required": ["claude_visual", "dominant"],
                "properties": {
                    "claude_visual": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "dominant": {"type": ["string", "null"]},
                },
            },
            "signals": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "labels_found",
                    "has_qr_or_barcode",
                    "magazine_x_brand_headline",
                    "contact_info_on_page",
                    "layout",
                ],
                "properties": {
                    "labels_found": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Verbatim strings of any advertorial labels found "
                            "on the page (e.g. 'Sponsored', '広告', 'Promotion')."
                        ),
                    },
                    "has_qr_or_barcode": {"type": "boolean"},
                    "magazine_x_brand_headline": {"type": ["string", "null"]},
                    "contact_info_on_page": {"type": "boolean"},
                    "layout": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "bleeds_to_edge",
                            "single_image_dominates",
                            "has_body_copy_columns",
                            "looks_like_ad",
                        ],
                        "properties": {
                            "bleeds_to_edge": {"type": "boolean"},
                            "single_image_dominates": {"type": "boolean"},
                            "has_body_copy_columns": {"type": "boolean"},
                            "looks_like_ad": {"type": "boolean"},
                        },
                    },
                },
            },
            "article_type": {
                "type": "object",
                "additionalProperties": False,
                "required": ["initial", "confidence", "evidence"],
                "properties": {
                    "initial": {"type": "string", "enum": ARTICLE_TYPES},
                    "confidence": {"type": "number"},
                    "evidence": {"type": "string"},
                },
            },
            "celebrity": {
                "type": "object",
                "additionalProperties": False,
                "required": ["present", "candidates", "evidence"],
                "properties": {
                    "present": {"type": "boolean"},
                    "candidates": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "evidence": {"type": ["string", "null"]},
                },
            },
            "bridal": {
                "type": "object",
                "additionalProperties": False,
                "required": ["present", "evidence"],
                "properties": {
                    "present": {"type": "boolean"},
                    "evidence": {"type": ["string", "null"]},
                },
            },
            "monography": {
                "type": "object",
                "additionalProperties": False,
                "required": ["present", "subject", "subtype", "evidence"],
                "properties": {
                    "present": {"type": "boolean"},
                    "subject": {"type": ["string", "null"]},
                    "subtype": {
                        "type": ["string", "null"],
                        "enum": ["product", "corporate", "testimonial", None],
                    },
                    "evidence": {"type": ["string", "null"]},
                },
            },
            "notes": {"type": ["string", "null"]},
        },
    },
}


# ── Pass 2: cross-page revision ──────────────────────────────────────────────
# Pass 2 emits one tool call per page with only the fields it can legitimately
# revise. Everything else is copied through from pass 1 verbatim by the runner.

PASS2_TOOL = {
    "name": "record_page_revision",
    "description": (
        "Record the post-context revision for a single page. Emit one tool call "
        "per page in the requested range. Omit revision_reason if final == initial."
    ),
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["image_id", "article_type", "monography"],
        "properties": {
            "image_id": {"type": "string"},
            "article_type": {
                "type": "object",
                "additionalProperties": False,
                "required": ["final", "confidence"],
                "properties": {
                    "final": {"type": "string", "enum": ARTICLE_TYPES},
                    "confidence": {"type": "number"},
                    "revision_reason": {"type": ["string", "null"]},
                },
            },
            "monography": {
                "type": "object",
                "additionalProperties": False,
                "required": ["present", "subject", "subtype"],
                "properties": {
                    "present": {"type": "boolean"},
                    "subject": {"type": ["string", "null"]},
                    "subtype": {
                        "type": ["string", "null"],
                        "enum": ["product", "corporate", "testimonial", None],
                    },
                },
            },
        },
    },
}
