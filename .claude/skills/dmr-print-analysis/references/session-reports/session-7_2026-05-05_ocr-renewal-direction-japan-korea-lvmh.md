# Print Data Entry (DMR) — Process Analysis

**Source:** Antonella Genovese, Francesca Boattini, Mariana Martella — 5 May 2026
**Focus:** OCR renewal direction (LLM vs. current pipeline), Japan/Korea methodology alignment, LVMH custom score impact on rule changes
**Format:** Open-agenda working session, structured here as Q&A around the topics actually discussed.

> **Transcription note:** The Zoom auto-summary of this session rendered "OCR" variously as **"CR"**, **"SIAR"**, and **"Content Recognition"**, and rendered "LLM" as **"LM"** and **"Elelem"**, and "LVMH" as **"VMH"** / **"MMH"**. None of these are real systems or entities — they are all transcription artifacts of the same underlying terms. This report uses canonical names: **OCR pipeline**, **LLM**, **LVMH**.

---

## 1. End-to-End Workflow (Actions)

This session did not introduce new workflow steps. It produced **direction-setting decisions** on top of the workflows already documented in Sessions 1–6. No update to §1 of `dmr-process-knowledge.md` is required.

---

## 2. Key Points

| Area | Detail |
|---|---|
| **OCR renewal direction (Margot + Pau)** [Updated: 2026-05] | Margot and Pau have a working hypothesis to renew the OCR pipeline by moving toward an **LLM-based approach**, rather than incrementally improving the current pipeline. Mariana flagged that she is not yet fully comfortable with the current OCR pipeline's mechanics — the engineering walkthrough in Session 6 partially addressed this gap. |
| **Why LLM (vs. keyword/alias matching)** | Per Mariana's framing in the session: the current Stage 2 matcher recognizes brands only by **keyword string match** against the alias list. An LLM could understand **context** and identify a brand both by name **and** by category/contextual cues (e.g., recognizing a product description without an explicit brand name, or disambiguating between two brands that share a partial name). |
| **Francesca's qualification** | Francesca agreed an LLM direction is plausible, but pointed out that the **quality of the input keyword/product spelling** remains a foundational issue — even an LLM downstream depends on having clean, correctly-spelled product entries upstream. Edge case raised: products with very similar names but slight spelling variations. |
| **OCR renewal — first technical milestones** | Mariana committed to: (1) defining all advertising spaces (ADV space taxonomy) as an input to the renewal scope; (2) advancing the technological assessment of the OCR pipeline (further investigation with Alberto on what's developable and how the alias/product catalogue should be structured). |
| **Magazines vs. dailies require different approaches** | Mariana flagged (referencing earlier skill analysis): page-type and periodicity classification should drive the renewal — dailies have specific layout patterns that differ from magazines and should be treated as a separate segment for any LLM/AI work. This aligns with the strategic takeaway from Session 1 ("start with dailies"). |
| **Pending follow-up with Silvana** | A meeting with Silvana on the OCR/AI renewal project is still outstanding. First milestones to bring to that meeting: (a) full ADV-space definition, (b) OCR technological progress. |
| **Japan / Korea methodology — open alignment question** | Methodology rules differ between Japan, Korea, and the global standard. Antonella confirmed she has shared **both the generic manual and the country-specific rules**, but flagged that the Japan-specific magazine documentation may need a refresh. Francesca will check with **Enoco** — who originally pushed strongly for the differentiation — whether the Japan/Korea-specific rules could now be partially aligned with the global standard. Several years have passed since the original differentiation; positions may have evolved. |
| **Risk flagged by Mariana on country-specific rules** | Mariana's concern: country-specific rule pools create blind spots. If a magazine **outside the named country pool** behaves the same way as a Japan/Korea title (e.g., uses similar Sponsored-label patterns), the system has no mechanism to detect and apply the right treatment. Country pools risk being too narrow to be defensive. |
| **LVMH custom score is the dominant constraint on rule changes** [Updated: 2026-05] | LVMH receives a **client-specific score** computed via **custom formulas** that depend on specific methodology flags. Some flags feed the LVMH formula; others do not. Any taxonomy simplification (flag merger, sub-line restructuring, etc.) **must be reviewed against the LVMH score** before adoption — a "neutral" change at the methodology level may not be neutral economically for LVMH reporting. Mariana explicitly distinguished between flags that impact the LVMH score and flags that don't. |
| **Numeric extract for Margot meeting** | Mariana to send the extracted numbers to Francesco after her upcoming meeting with Margot (operational item, no methodology content). |

---

## 3. Pain Points

### A. Data Entry Complexity
*(No new pain points raised in this session.)*

### B. Process / Procedure

| Pain Point | Impact |
|---|---|
| **Country-specific rule pools may be defensively too narrow** [Updated: 2026-05] | Rules currently scoped to Japan/Korea may apply equally to publications in other countries that exhibit the same patterns (e.g., systematic Sponsored labels on editorial content). The current taxonomy has no mechanism to apply Japan/Korea-style structural-override logic to a publication outside that named pool. **Source:** Mariana's concern raised in this session. **Cross-reference:** Session 5 § Japan/Korea structural override + general-rules.md §6. |
| **Renewal scope ambiguity: incremental OCR improvement vs. LLM rewrite** [Updated: 2026-05] | Two parallel directions are alive: (a) the incremental Session-6 improvements (LLM-assisted reading-order on Google Vision JSON, multilingual alias dictionary); (b) Margot/Pau's deeper LLM-direction renewal. The two are not yet reconciled into a single roadmap. |

### C. Dependencies on Other Teams / Vendors

| Pain Point | Impact |
|---|---|
| **LVMH custom score creates a hidden veto on methodology changes** [Updated: 2026-05] | Any rule change must be screened for LVMH formula impact before adoption. This adds a review gate that is currently undocumented and dependent on knowing which flags feed the formula. The mapping of flags-to-LVMH-score is not codified in the skill. |
| **Japan/Korea rule alignment depends on Enoco's input** | Re-aligning the Japan/Korea methodology to the global standard requires Enoco's agreement (they originally drove the differentiation). Until that conversation happens, no rule consolidation can proceed. |

---

## 4. Easily Automatable Opportunities

### Quick Wins (rule-based, no AI)
*(No new quick wins from this session.)*

### Medium-term (OCR / text extraction)

| Opportunity | Mechanism |
|---|---|
| **OCR renewal: LLM-direction renewal (Margot/Pau hypothesis)** [Updated: 2026-05] | Move beyond Stage 2 keyword/alias matching toward an LLM that recognizes brands and products both by name and by contextual/category cues. Differentiated from R_ocr (LLM-assisted reading-order on Google Vision JSON, see Session 6) — this is a deeper rewrite of Stage 2, not a post-Stage-1 enhancement. Prerequisite for scoping: clean and consistent input keyword/product taxonomy (Francesca's qualification). |
| **Renewal segmentation: magazines vs. dailies as separate streams** [Updated: 2026-05] | Treat dailies and magazines as **distinct segments** in the renewal scope. Dailies have simpler, more uniform layouts and a narrower methodology surface area — they are the natural pilot for an LLM-based approach (consistent with Session 1 strategic takeaway). Magazines come second, after caption detection is solved. |

### Longer-term (AI-assisted)
*(No new longer-term opportunities from this session.)*

---

## 5. Strategic Takeaways

**Two OCR-renewal directions need to be reconciled.** Session 6 (with Alberto/Suril) outlined incremental, additive improvements: LLM-assisted reading-order reconstruction on top of Google Vision, multilingual alias dictionary, open-source Stage 1 benchmark. This session (with Antonella/Francesca, channeling Margot/Pau) outlined a deeper rewrite — moving Stage 2 itself toward an LLM that understands context, not just strings. These are not the same project. Mariana's open action: investigate the difference between "advanced OCR" (incremental) and **LLM-based** (rewrite) approaches before any commitment.

**Input quality is a precondition for any LLM downstream.** Francesca's point lands: an LLM that classifies products only works if products are entered with clean, consistent spelling. The product/keyword taxonomy upstream of any AI is itself an investment area. Cleaning the alias/product catalogue is therefore not optional even in an LLM-rewrite scenario.

**LVMH custom score is the operative constraint on any rule simplification.** Methodology cleanups (flag mergers, sub-line restructuring, gender-flag separation, etc.) cannot be evaluated only on a methodology basis — they must be priced against the LVMH formula. The mapping of flags to LVMH-score impact should be documented and consulted before any taxonomy change is proposed.

**Country-specific rule pools are operationally defensible but structurally fragile.** The Japan/Korea structural-override logic (Session 5) works because the publications behave consistently, but it does not generalize to similar publications outside the named pool. Re-checking with Enoco whether the differentiation is still warranted is the right next step. Independently, the underlying logic (Sponsored-label-with-editorial-structure → editorial) may deserve to become a general detection rule rather than a country-pool rule.

**Dailies remain the natural first pilot for any AI work.** Reaffirmed across sessions (1 and 7): simpler methodology, more uniform layout, fewer edge cases. Any LLM-direction renewal should start there.
