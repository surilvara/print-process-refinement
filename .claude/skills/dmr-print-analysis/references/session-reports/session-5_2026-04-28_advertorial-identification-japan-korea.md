# Print Data Entry (DMR) — Process Analysis

**Source:** Antonella Genovese + Mariana Martella, approx. 28 April 2026
**Focus:** Advertorial identification training; Japan/Korea PR classification issues; operational PR rules; Claude skill onboarding for Antonella

---

## 1. End-to-End Workflow (Actions)

This session did not cover a new end-to-end workflow. It focused on the **decision process for identifying advertorials/PR pages**, specifically:
- How operators are trained to distinguish ADV vs. editorial vs. PR visually
- The Japan/Korea exception for ubiquitous "Sponsored" labels
- The rule for PR when no label is present
- A live demonstration of the DMR Print Analysis skill in Claude

---

## 2. Key Points

### A. Training: ADV vs. Editorial vs. Advertorial

| Topic | Detail |
|---|---|
| **First-day training approach** | Antonella physically opens the magazine with the new operator and shows the graphic difference between a pure advertising page and an editorial page. Visual recognition is primary. |
| **Pure ADV characteristics** | Almost no text. Shows a product. Brand name. Brand website at the bottom. No redattore/fotografo credits. No page number in the typical editorial sequence. |
| **Advertorial (PR) characteristics** | Has editorial-style text but is paid content. Identified by a label (see list in general-rules.md) or by a combination of secondary features. The decision flowchart in the manual is used for ambiguous cases. |
| **Flowchart as disambiguation tool** | Antonella uses the decision grid (flowchart) from the manual when in doubt. It asks a series of Yes/No questions about layout, labels, editorial details, and contributor presence in staff. |
| **Sommario and staff as verification tools** | Key checks: Is the page indexed in the sommario? Are the credited redattore/fotografo present in the magazine's staff list? YES to both → more likely editorial. |

### B. Japan/Korea PR Classification

| Topic | Detail |
|---|---|
| **The problem** | In Japanese and Korean magazines, "Sponsored" and "In Collaboration With" appear on many pages — including legitimate editorial pages. This is a cultural/regulatory convention. |
| **Previous rule** | Treat any page with "Sponsored" as PR. |
| **Current operational rule** | Assess the full editorial structure: if the page has staff-credited redattore/fotografo, a page number, sommario indexing, and consistent layout → **Editorial** despite the label. The label alone is insufficient to classify as PR. |
| **QC escalation** | When ambiguous, Italy/international QC contacts the Japan/Korea responsible operator (Noko, Giovanna, or China equivalent) to confirm. The classification is made per-publisher: Condé Nast Japan (Vogue Japan) consistently uses "Sponsored" on editorial content → not treated as PR unless structure is clearly different. |
| **Pending revision** | Antonella flagged this area as needing a formal updated unified rule. France has also expressed intent to revise. Changes can only be implemented at semester or year boundary. Until then: case-by-case with escalation. |
| **PEN magazine (2020 rule)** | PEN was reclassified in 2020. Within PEN, a one-brand article with contact info is only an advertorial if it is NOT in the sommario AND carries no page number. If both sommario presence and page number are present → Editorial. See `advertorials.md` for full detail. |

### C. PR When No Label Is Present

| Topic | Detail |
|---|---|
| **Rule** | If a page looks like an advertorial (editorial-style text + single brand product) but carries NO identifying label → entered as **ADV**, not PR. |
| **Rationale** | Reader's point of view: the reader cannot identify it as paid content without a label. |
| **Consequence** | Same brand may accumulate both PR pages (labelled issues) and pure ADV pages (unlabelled issues) across a year. This is intentional. For MIV purposes, both PR and ADV count as paid; the distinction matters less than not missing the page. |
| **Adjacent page case** | If a labelled PR and an unlabelled ADV for the same brand appear on facing pages: ADV team enters the labelled one as PR and the unlabelled one as ADV. If neither is labelled → both as ADV. |

---

## 3. Pain Points

| # | Pain Point | Impact |
|---|---|---|
| 35 | **Japan/Korea "Sponsored" label ubiquity** — the same label that triggers PR classification in other markets is used routinely even for legitimate editorial content in Japan/Korea. | Requires manual case-by-case QC escalation; not automatable without publisher-specific rules. |
| 36 | **No unified, up-to-date written rule for Japan/Korea advertorials** — the current handling is experience-based (Noko, Giovanna, Antonella). The old manual rule is acknowledged to be outdated. | Knowledge is at risk of being lost if these operators leave. France has agreed it needs revision but no timeline. |
| 37 | **PR/ADV boundary on unlabelled pages is inconsistent across operators** | Some operators may classify a Caudalie-style text-heavy ADV page as PR; others as ADV. Antonella has standardised this within her team (no label = ADV) but it may not be uniform globally. |

---

## 4. Easily Automatable Opportunities

No new automation opportunities emerged from this session beyond those already documented.

---

## 5. Strategic Takeaways

**The advertorial identification process is primarily visual and experiential.** Antonella's training approach is hands-on (opening the magazine physically). A written flowchart exists for disambiguation but is secondary to visual recognition. Automation of advertorial detection would require reliable layout analysis.

**Japan/Korea represent a known classification exception zone.** The existing rule is operationally functional but undocumented formally. Until France/Francesca issue a revised rule, the live practice is: structural analysis (staff, sommario, page number) overrides label-based classification for Japan/Korea.

**PEN (2020) is the only magazine with a formally updated Japan tie-up rule.** All other Japan magazines follow the 2016/2017 flowchart with the structural-analysis overlay.

**The Claude skill sharing session revealed an onboarding need:** Antonella is now aware of the skill structure and has access to the shared skill. She identified a use case (using the skill to answer classification doubts at query time). The main barrier is knowing how to interact with skills effectively — Mariana offered to co-build Antonella's own skills as an onboarding path.
