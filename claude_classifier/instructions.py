context_prompt = """
You are classifying pages from print newspapers/ magazines. Assign exactly one of: 'advertising', 'editorial', or 'advertorial'.

ADVERTISING
- Minimal text; primarily showcases a product or brand
- Includes brand name and/or website; no editorial contributor credits (journalist/photographer)
- No page number in the editorial sequence
- If a page resembles an advertorial but carries NO identifying label → classify as advertising

EDITORIAL
- Contains staff-credited journalist and/or photographer
- Has a page number in the editorial sequence
- Indexed in the magazine's sommario (table of contents)
- Note: in Japanese/Korean magazines, labels like "Sponsored" or "In Collaboration With" may appear on genuine editorial pages — assess the full editorial structure (staff credits, page number, sommario) rather than relying on the label alone

ADVERTORIAL
- Editorial-style layout and text, but is paid/sponsored content
- Must carry an explicit identifying label (e.g. "Advertorial", "Sponsored", "Special Advertising Section", "In Collaboration With", etc.)
- No staff-credited journalist/photographer from the magazine's own editorial team
- Typically not indexed in the sommario and/or lacks a standard page number
- If facing an unlabelled page for the same brand, that page is advertising; only the labelled page is advertorial

Provide your response in this format:
{
    "classification": "advertising" | "editorial" | "advertorial",
    "reason": "explanation of the classification",
    "confidence": 0.0-1.0
}
"""
