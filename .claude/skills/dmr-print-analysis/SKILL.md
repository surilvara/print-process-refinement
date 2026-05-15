---
name: dmr-print-analysis
description: "Map, document, and analyze DMR print workflows. Also a knowledge base for editorial classification, fashion/beauty monitoring methodology, advertorials, and product categorization."
---

# DMR Print Data Entry Analysis

## Overview

This skill serves two purposes:

1. **Knowledge base (Q&A)** — Answer questions about the DMR print data entry process, its workflows, tools, terminology, rules, edge cases, pain points, and automation opportunities.
2. **Transcript analysis** — Analyze new transcripts from immersive sessions with DMR operators and produce structured reports.

All responses must be in **English**, regardless of the language used by the user or in the source material.

---

## Knowledge Base — Reference File Index

The knowledge base is split into multiple reference files by topic. **Always consult the relevant file(s) before answering.** If a question spans multiple topics, read all relevant files.

| File | Contents | When to read |
|---|---|---|
| `references/dmr-process-knowledge.md` | End-to-end workflow, actions, glossary, key points, pain points, automation opportunities, strategic takeaways from operator sessions. | Questions about the workflow, Web Digital UI, priority system, scanning, page numbering conventions, team structure, or automation. |
| `references/fashion-methodology.md` | Complete fashion monitoring rules: cover, gatefold, multiple covers, TOC, double pages, still life, credits on model, total look, celebrities, contextualization, recognized products, location, monographies (product/corporate/testimonial), fashion in beauty stories, special situations, product lines, evaluation. | Any question about how fashion editorial or fashion data is entered, classified, or valued. |
| `references/beauty-methodology.md` | Complete beauty monitoring rules: beauty categories, worn beauty products, cover page beauty, TOC beauty, beauty in fashion articles, beauty in beauty articles, beauty product taxonomy, bath range vs. mass market, captions & type of communication. | Any question about how beauty editorial or beauty data is entered, classified, or valued. |
| `references/training-rules.md` | Compiled operator training rules: single vs. double pages, costume jewellery vs. jewellery, high jewellery vs. jewellery (new rule), product monographies, testimonial & monographies, contextualization, beauty in fashion articles, beauty in beauty articles, multiple covers, collaboration brands, beauty products taxonomy. | Questions about specific classification decisions, edge cases, or "how do I classify X?" |
| `references/inserts-and-registration.md` | Insert classification (gatefolds, bonded inserts, loose inserts, samples), scanning procedures, registration (check-in) manual, image upload. | Questions about physical magazine processing, insert types, scanning workflow, or registration procedures. |
| `references/RULES DOC/inserts-classification-registration.md` | **Comprehensive insert manual** combining Italian (Omniapress 2015) and English (international) sources. Full classification of all insert types: gatefolds/battenti (C1 and C2), BC Recto/Verso (bianca e volta), BC Page, BC Booklet (3 sub-variants), BC Folder (including split-magazine folders), BC Group, BC Postcard, Loose Inserts (LC). Page numbering conventions, scanning instructions, valuation rules, Campione Prodotto field usage. | Any question about insert types, how to number/register/scan inserts, how to value them, edge cases (glued booklet, split folder, mall catalogue). **Supersedes and extends** `inserts-and-registration.md`. |
| `references/advertorials.md` | Advertorial and tie-up rules, including Japan-specific rules (2016+2017 versions), obvious/less obvious features, exceptions, trade association pages, contest/event rules. **Now includes:** updated Japan flowchart (2017/2018), PEN magazine new rule (2020) — sommario+page-number tie-break for tie-up classification. | Questions about how to identify or classify advertorial vs. editorial content, especially for Japan. **For Japan/Korea "Sponsored" label edge cases, also read `general-rules.md` §6.** |
| `references/RULES DOC/general-rules.md` | **General rules manual** covering: publications with embedded translations (3 scenarios), "Le Aziende Informano" sections (space calculation), publiredazionali (identification criteria, decision flowchart, trade association exception), tie-ups in Japanese magazines (identification + 3 exceptions), sponsored magazines (full-sponsor vs. mixed-sector, distinction from "in association with" supplements and ad catalogues). **Now includes:** §6 Japan/Korea "Sponsored" label ubiquity and structural-override rule, §7 PR-when-no-label rule (unlabelled pages → ADV not PR). | Questions about translated editions, advertorial identification, Japanese tie-ups, sponsored supplements, or the "Le Aziende Informano" format. **Cross-reference with `advertorials.md`** for additional tie-up and publiredazionale detail. |
| `references/RULES DOC/stores-ecommerce.md` | Rules for entering stores and e-commerce sites cited in captions. Store/e-commerce brand mirrors the product brand record exactly (same sub-line, value, tipo di comunicazione, objects, celebrities) + Marchio Commercializzato field set to the product brand. Applies to all sectors. Worked examples included. | Any question about how to handle "at [store]" or "at [website]" captions, or about the Marchio Commercializzato field. |
| `references/glossary.md` | Unified glossary of all DMR terms: system/UI terms, page fields, naming conventions, insert types, classification & methodology terms, article types. Consolidated from all other reference files. | Quick term lookup. Read first when the user asks "what does X mean?" or when you need to verify the exact definition of a term before answering. |
| `open-questions.md` | **Living checklist of open questions and knowledge gaps** — unresolved rules, ambiguous classifications, missing documentation, pending revisions. 29 items across 6 areas (Advertorial/PR, Japan/Korea, ADV fields, Mail Quotidiana/OCR pipeline, Editorial Methodology, Skill Maintenance). Each item has an ID (OQ-01…OQ-29), source, and status (OPEN/RESOLVED). | When the user asks what is still unclear or unresolved, or wants to mark an item as resolved. When adding a new session transcript, check if any open question is answered and update accordingly. |
| `references/session-reports/` | Archive of structured analysis reports from operator immersive sessions. Each file follows the standard report template (Workflow → Key Points → Pain Points → Automation → Takeaways). | When the user asks about a specific session, wants to compare sessions, or needs the raw analysis before it was merged into the knowledge base. |

**Session reports index:**

| File | Session focus |
|---|---|
| `session-1_issue-level-workflow.md` | Issue selection, priority system, page header creation (Antonella + Francesca) |
| `session-2_2026-04-14_record-level-data-entry.md` | Record-level data entry: brand/sub-line, tipo comunicazione, marchio commercializzato, contextualization, celebrity, season (Antonella, 14 Apr 2026) |
| `session-3_2026-03-26-27_marie-claire-timing-analysis.md` | Timing analysis: average time per enrichment action, per-page breakdown, session pace, delta distribution — Marie Claire Issue 10810796, operator 345 (26–27 Mar 2026) |
| `session-4_2026-04-17_adv-insertion-mail-quotidiana.md` | ADV page-level and record-level data entry workflow; insert types (battente, biancavolta, booklet); ADV-specific fields (CoAdv, PR flag, Campione Prodotto, Posizione in pagina, Celebrity); Mail Quotidiana program — brand-only entry, caption-vs-product placement rule, group management, OCR limitations (Francesca Boattini + Mariana Martella, Apr 2026) |
| `session-5_2026-04-28_advertorial-identification-japan-korea.md` | Advertorial visual identification training; Japan/Korea "Sponsored" label ubiquity and structural-override rule; PR-when-no-label rule (ADV not PR); PEN 2020 sommario+page-number tie-break; escalation to Japan/Korea operators for ambiguous cases; pending formal rule revision (Antonella Genovese + Mariana Martella, 28 Apr 2026) |
| `session-6_2026-05-05_ocr-pipeline-architecture.md` | OCR pipeline architecture: Print Image Management app, Google Vision API (Stage 1), DMR custom brand-alias matcher (Stage 2 — Alberto + Massimiliano), `OCR_Image_Queue` table, output tables (Image_Brand, Image_Brand_Word), bounding-box coordinates, multi-column brand-split limitation, open-source OCR evaluation, LLM-assisted reading-order. (Alberto Tornielli + Suril Vara + Mariana Martella, 5 May 2026) |
| `session-7_2026-05-05_ocr-renewal-direction-japan-korea-lvmh.md` | OCR renewal direction (Margot/Pau LLM-direction hypothesis vs. Session 6 incremental track); input-quality precondition for LLM downstream; Japan/Korea methodology alignment via Enoco; LVMH custom-score constraint on rule simplification. (Antonella Genovese + Francesca Boattini + Mariana Martella, 5 May 2026) |

---

## How to answer Q&A

1. Read the relevant reference file(s) from the index above.
2. Answer based strictly on what the documents contain. If the answer is not covered, say so clearly and suggest it may need to be added.
3. Use precise DMR terminology as defined in the Glossary section of `dmr-process-knowledge.md`.
4. Keep answers concise and actionable. Point to the relevant reference file and section if the user wants more detail.
5. When referencing system fields, actions, or screens, use the exact names from the Glossary.

### Example Q&A — Process Mapping

**Example 1: High-level workflow**
Q: "Describe the end-to-end workflow for editorial data entry on a magazine issue."
A: Read `dmr-process-knowledge.md`, section "1. End-to-End Workflow (Actions)". Walk through all 10 steps in order, using the exact system terms (Gestione Uscite, Scadenza Testate, Fine Scansione, EDI, etc.). Mention the hard dependencies (scan must be complete, cover must be set first).

**Example 2: Pain points and bottlenecks**
Q: "What are the main bottlenecks in the print data entry process?"
A: Read `dmr-process-knowledge.md`, section "3. Pain Points". Organize the answer by category (Data Entry Complexity / Process / Dependencies). Highlight the ones with highest impact: fully manual page numbering, brand search from a huge list, scan dependency as a hard gate.

**Example 3: Automation opportunities**
Q: "What could we automate in the short term without AI?"
A: Read `dmr-process-knowledge.md`, section "4. Easily Automatable Opportunities — Quick wins". List the four rule-based opportunities (auto-create presumed issues, pre-fill cover metadata, auto-assign facciata, sequential page-number suggestion) with a one-line explanation of how each works.

---

## Transcript Analysis

When the user provides a new transcript and asks for an analysis, produce a structured report in **Markdown** following this exact structure:

```
# Print Data Entry (DMR) — Process Analysis

**Source:** [session participants, date if available]

---

## 1. End-to-End Workflow (Actions)
## 2. Key Points
## 3. Pain Points (A. Data Entry Complexity / B. Process / C. Dependencies)
## 4. Easily Automatable Opportunities (Quick wins / Medium-term / Longer-term)
## 5. Strategic Takeaways from the Discussion
```

### Per-section instructions

- **§1 End-to-End Workflow:** List each distinct action/step mentioned, in chronological order. Use the exact terminology from the Glossary in `dmr-process-knowledge.md`. Flag any steps not already documented. If the transcript describes a variation of an existing workflow (e.g., ADV vs EDI), note the differences explicitly.
- **§2 Key Points:** Extract factual findings as a table (Area | Detail). Focus on things that are operationally significant: rules, constraints, system behaviors, team structure. Do not include opinions or speculation.
- **§3 Pain Points:** Categorize each pain point under A (Data Entry Complexity), B (Process/Procedure), or C (Dependencies on Other Teams). For each, state the pain point and its impact. If a pain point was already documented, note "Confirms existing" and add any new detail. If it's new, mark with **NEW**.
- **§4 Automatable Opportunities:** Separate into Quick wins (rule-based, no AI), Medium-term (OCR/text extraction), and Longer-term (AI-assisted). For each, describe what could be automated and how. Be specific about the mechanism, not just the goal.
- **§5 Strategic Takeaways:** Capture high-level conclusions, consensus, disagreements, or decisions made during the discussion. Include direct implications for process improvement planning.

### Analysis Guidelines

- **Cross-reference with existing knowledge.** Read relevant reference files first. Note if the transcript confirms, contradicts, or expands existing knowledge.
- **New findings.** Highlight with "**NEW:** This was not documented in previous sessions".
- **Transcription quality.** Auto-generated transcripts may be garbled, mixed-language. Interpret intelligently using DMR domain knowledge.
- **Tone.** Factual, concise. Working document, not meeting summary.
- **Output.** Always produce as a `.md` file saved to `/mnt/user-data/outputs/`.

---

## Updating the Knowledge Base

### A. Merging findings from a new transcript analysis
Integrate into the relevant file(s). Do not duplicate — merge intelligently. Preserve existing structure.

### B. Adding operator rules, guidelines, or reference material directly
Integrate faithfully — do not summarize or simplify operational rules unless asked. If it contradicts existing content, flag and ask the user. If it doesn't fit an existing file, create a new one and update this SKILL.md index.

### C. Rule versioning convention
When adding or updating a rule, tag it with `[Updated: YYYY-MM]` next to the section heading or rule statement. This signals to both Claude and the user whether a rule is recent or long-established. Examples:

- `## 3. High Jewellery vs. Jewellery [Updated: 2024-06]`
- `## 10. Collaboration Brands [Updated: 2025-01]`

When answering questions, if a rule carries an `[Updated]` tag, mention that it is a recent update so the user knows it may not yet be fully adopted by all operators.

---

## Edge Cases & Reminders

- The user (Mariana) manages process improvement for DMR. Answer thoroughly regardless of question complexity.
- EDI (editorial) and ADV (advertising) are fundamentally different workflows. Never conflate them.
- "Methodology" = rules for data classification (service types, sectors, values), not workflow steps.
- Fashion methodology and beauty methodology have different rules for the same situations (e.g., cover, TOC, space allocation). Always specify which sector's rules apply.
- **LVMH custom score** [Updated: 2026-05]: LVMH receives a client-specific score computed via custom formulas distinct from MIV. Some methodology flags feed this formula, others do not. **Any rule simplification, flag merger, or sub-line restructuring proposal must be screened against the LVMH formula before adoption** — methodologically neutral changes are not always economically neutral. The flag-to-LVMH-score mapping is not yet codified (tracked as OQ-28). When the user asks about consequences of a methodology change, raise the LVMH-score check as a default consideration.

### ADV-specific rules (from session 4)
- **Cover + contapagine**: whichever team (ADV or EDI) opens the issue first must assign the cover and run the page count — there is no fixed ownership rule.
- **Double-page ADV**: same creative = 1 record, quantità 2. Two different creatives on the same double page = 2 records, quantità 1 each, value = full page each.
- **Inserts (free-standing)**: always valued as 1 full page regardless of number of insert pages. Bound inserts: valued by space occupied.
- **Biancavolta**: insert type where the front and back of a page are the same brand's ad. Format = "1×2", always 2 pages.
- **PR flag (Publiredazionale)**: either ADV or EDI team can set this flag. Always counts as ADV in client analysis. Use minimum number of sub-lines (typically 1).
- **CoAdv / PTD**: ad paid by two parties (brand + retailer, or two brands). Highly contested classification; grey areas exist. Not suitable for automation in near term.
- **Campione Prodotto**: physical sample attached to the page. Relevant only for publisher reports; no impact on MIV.
- **ADV closure**: operator must manually click "Terminato" / "Fine Inserimento ADV" to stamp closure date. Not automatic.

### Mail Quotidiana rules (from session 4)
- **Separate program**: Mail Quotidiana runs in a completely separate system from EDI/ADV. Data does not flow between them.
- **Brand-only entry**: only the brand name is entered. No sub-line, product, value, season.
- **Caption placement rule**: brand must be entered on the page where the product is **visually shown**, NOT on the page with the caption/credits (which may be on a different or later page). This is the primary placement rule and a key challenge for automation.
- **Brand scope**: narrower than EDI. Each publisher group has its own brand list. Not all brands have mail quotidiana coverage.
- **OCR pipeline dependency** [Updated: 2026-05]: Mail Quotidiana brand detection is powered by the DMR OCR pipeline (Google Vision + DMR custom brand-alias matcher). Limitations: brand alias dictionary covers only Western scripts (misses Cyrillic/Arabic/CJK); multi-word brands split across columns are missed because Google Vision splits text by whitespace alone with no semantic understanding. These are the #1 and #2 OCR improvement priorities (per Francesca and Alberto respectively). See `dmr-process-knowledge.md` §6 for full architecture. **Note:** earlier auto-transcripts mistranscribed "OCR" as "SIAR" — there is no system called SIAR.
- **Caption detection is the primary AI blocker**: Francesca will not proceed with AI-assisted mail quotidiana or EDI automation until caption detection is demonstrably solved at test level (not just development level). This must be the first AI capability to validate.

### OCR pipeline architecture (from session 6) [Updated: 2026-05]
- **Two stages, one pipeline**: Stage 1 = Google Vision API for text extraction (returns hierarchical JSON with bounding boxes per character); Stage 2 = DMR custom brand-alias matcher (Alberto + Massimiliano), iterates symbol-by-symbol through the JSON, matches against alias list, writes to `Image_Brand` and `Image_Brand_Word` tables.
- **Bounding-box coordinates** power the yellow highlight rectangle in the operator UI. Any future Stage 1 replacement must preserve coordinate output.
- **Volume**: ~4M images/year through Google Vision — material recurring cost. Open-source evaluation is in progress (Suril) but no replacement has matched accuracy yet.
- **Highest-leverage near-term improvement** (per Alberto): apply an LLM **after** Google Vision (on its JSON output) to reconstruct correct article reading order on multi-column layouts. Resolves the dominant Stage 2 failure mode.
- **The pipeline stays live regardless of broader AI roadmap** because Discover uses OCR text content for keyword search inside print articles. New AI is additive, not a replacement.
- **Queue table**: `OCR_Image_Queue`.

### Source authority hierarchy

When two or more reference files provide conflicting information on the same topic, apply this priority order:

1. **`training-rules.md`** — highest authority. Contains the most recent operator training decisions, including explicit rule updates (e.g., "New Rule from Jan 2025"). Always prevails.
2. **`fashion-methodology.md` / `beauty-methodology.md`** — sector-specific monitoring rules. Prevail over process knowledge for classification questions.
3. **`dmr-process-knowledge.md`** — workflow and process documentation. Lowest priority for classification rules, but primary source for process mapping questions.

`advertorials.md` and `inserts-and-registration.md` cover separate domains and rarely conflict with the above. If they do, flag the conflict to the user.

## References
- `references/DMR_Timing_Baseline_Report.md` — EDI data entry timing analysis documentation; read when performing or discussing EDI entry timing analysis.
