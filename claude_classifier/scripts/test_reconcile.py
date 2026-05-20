"""Quick self-test for the vendored DMR matcher + reconcile pipeline.

Run with: ``uv run python -m claude_classifier.scripts.test_reconcile``
"""

from pathlib import Path

from claude_classifier.reconcile import (
    extract_ocr_text,
    load_canonical_brands_for_text,
)


def main() -> None:
    print("--- direct text test ---")
    text = (
        "I love Saint Laurent and Tiffany & Co. shoes. "
        "Also: nylon skirt, SAINT LAURENT BY ANTHONY VACCARELLO."
    )
    for b in load_canonical_brands_for_text(text):
        print(f"  {b.entity_type}: {b.name!r}")

    sample_ocr = Path("ocr_eval/googlevision_output/vogue_uk_2026-04-01/42524838.json")
    if sample_ocr.exists():
        print(f"\n--- real page test ({sample_ocr.name}) ---")
        text = extract_ocr_text(sample_ocr)
        print(f"  OCR length: {len(text)} chars")
        for b in load_canonical_brands_for_text(text):
            print(f"  {b.entity_type}: {b.name!r}")


if __name__ == "__main__":
    main()
