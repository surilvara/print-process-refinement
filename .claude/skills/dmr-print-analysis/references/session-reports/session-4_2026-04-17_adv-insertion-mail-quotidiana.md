# Print Data Entry (DMR) — Process Analysis

**Source:** Francesca Boattini + Mariana Martella, session date approx. April 2026 (transcript timestamp 15:43–17:25)
**Focus:** ADV (advertising) page-level data entry workflow + Mail Quotidiana service

> **⚠️ Transcription note [added 2026-05]:** This session's auto-transcription rendered "OCR" (pronounced "oh-see-arr" in English) as **"SIAR"** throughout. There is no system called SIAR — every occurrence below should be read as **"OCR"**. The mistranscription has been corrected in this report.

---

## 1. End-to-End Workflow (Actions)

### ADV Insertion Workflow

1. **Access issue via Gestione Uscite** — navigate to the magazine issue. The ADV team typically inserts before the editorial team because ADV veloci reports must be extracted and sent to publishers on the day of publication.
2. **Assign cover + page count (contapagine)** — whichever team (ADV or EDI) opens first is responsible for associating the cover and performing the page count. This is a hard dependency for both teams.
3. **Navigate to ADV page entry** — select the page in the issue.
4. **Fill page-level fields (mandatory)**:
   - Numero pagina (page number)
   - Facciata (page side: left/right)
   - Posizionamento (positioning)
   - Formato (page size/format)
   - Image (optional: attach image to the page)
5. **Handle inserts (if applicable)** — if the page is part of an insert:
   - Classify as inserto, battente, or other type
   - Set formato: expressed as multiplier × pages (e.g. "1×2 pages" for a gatefold, "1/3" for a small booklet)
   - Associate insert pages to a pre-created insert record via the "Associa Inserto" button
   - To create an insert record: create dummy pages, fill in insert metadata (format, brand, description), save, then delete the dummy pages
6. **Fill record-level fields (one record per creative)**:
   - Marchio (brand)
   - Sottolinea (sub-line/product category)
   - Prodotto (product, if identifiable)
   - Quantità: 2 for double-page (same creative), 1 for single page or two different creatives within the same double page
   - Valore (space value — uses the same scale as editorial: full page, half page, etc.)
   - Stagione (season of the campaign, not the magazine issue)
   - Campione Prodotto (product sample flag: banda profumata, sample, tessera, cartolina — relevant for publisher reports)
   - PR flag (publiredazionale — marks ads resembling editorial content)
   - Bridal Product flag
   - CoAdv / PTD flag (co-advertising: ad paid by two brands or a brand + retailer)
   - Regalo con Acquisto flag (gift-with-purchase)
   - Posizione in pagina (page position: finestrella, banner, box, piedino — mainly for dailies)
   - Celebrity (type to search, add, system counts automatically)
   - Codice eliminazione (elimination code, set by account managers, not data entry)
7. **Handle multi-record pages** — create separate records when two different creatives appear on the same double page (e.g., two different products of the same brand, or two different product categories). Use full-page value for each, not half-page.
8. **Declare ADV insertion complete** — click "Terminato" / "Fine Inserimento ADV" button. This triggers the ADV closure timestamp visible in Gestione Uscite.

### Mail Quotidiana Workflow (separate program)

1. **Morning arrival registration** — when a magazine arrives physically, its arrival is registered. This populates the mail quotidiana queue.
2. **Access mail quotidiana program** — separate from the EDI/ADV system; the two are not connected.
3. **Select issue** — choose country → publication → date/issue from dropdowns.
4. **Load vertical gallery** — pages displayed as vertical pairs (cover alone on right, then all pages paired left-right).
5. **Link/unlink double pages** — an internal link button between each pair allows the operator to confirm or break double-page associations.
6. **Open page** — a simplified data entry mask opens.
7. **Enter brand names only** — only the brand name is entered (no sub-line, no product, no value, no season). System uses this for brand detection only.
8. **Page placement rule** — brand must be entered on the page where the product is visually shown, NOT on the page containing the caption/credits (which may be on a different page).
9. **PDF highlighting** — the system generates a highlighted PDF for monitoring: one version shows only the brands in the mail quotidiana scope; another shows all brands from the EDI insertion scope.
10. **Brand scope is narrower** — not all brands have mail quotidiana coverage. Each publisher group manages a list of brands associated with their email groups.
11. **Group management** — email groups managed within the mail quotidiana program: each group has recipient email addresses and associated brand list. Data is extracted and sent per group.

---

## 2. Key Points

| Area | Detail |
|---|---|
| ADV insertion order | No formal rule; ADV team often goes first because ADV veloci reports are delivered same day. The first team to open an issue also assigns the cover and runs the page count. |
| Cover + page count responsibility | Shared: first team to open assigns cover and performs contapagine. |
| Inserts — value rule | A loose (free-standing) insert of any number of pages is valued as 1 full page. A bound insert inside the magazine is valued based on the space it occupies (same scale as regular pages). |
| Insert format field | Expressed as multiplier × pages (e.g. "1/3" for booklet of 1/3 page size, "1×4" for a 4-page gatefold poster). Format captures size, not type (battente, booklet, folder all treated the same for value purposes). |
| Biancavolta | A specific insert type: the front and back of a page are both advertising for the same brand. Always 2 pages. Entered as an insert with format "1×2". |
| Double-page ADV with same creative | Use 1 record, quantità = 2. |
| Double-page ADV with 2 different creatives | Use 2 records, quantità = 1 each, value = full page each. Even if the two pages belong to the same brand. |
| Sub-lines with gender | ADV sub-lines include gendered variants (Abbigliamento Uomo/Donna, Profumo Uomo/Donna). If a single creative shows both genders, use the combined sub-line (e.g. "Uomo/Donna"). If two separate creatives are shown, use separate records. Proposal to split gender into a flag separate from sub-line — not yet implemented. |
| Season field (ADV) | Season of the campaign creative, not the magazine issue date. Fashion sub-lines: season changes can be inferred from creative visuals. For accessories, jewellery, watches: follow the magazine publication period (approx. Dec–May = SS, Jun–Nov = AW). Consult Silvana for exact changeover dates. |
| PR flag (Publiredazionale) | Can be inserted by either ADV or EDI team depending on which team identifies it. Always counts as ADV in client analysis regardless of which team inserted it. Rule: use the minimum number of sub-lines for a publiredazionale (typically 1, not an exhaustive list). |
| CoAdv / PTD flag | Marks an ad paid by two parties (brand + retailer, or two brands). The cost split is implicit from having two records on the same page — the flag is additional metadata for filtering. Grey area: clients sometimes dispute classification. |
| Campione Prodotto | Flags physical samples attached to the page (banda profumata, sample, tessera, cartolina). Relevant only for publisher reports (ADV veloci). No impact on MIV. Usage has declined — banda profumata was once very common (especially fragrances); now less frequent. |
| Posizione in pagina | Small-format position within the page (finestrella, banner, box, piedino). Used mainly for daily newspapers; rare in magazines. Relevant for publisher reports. |
| Celebrity field | Type first letters → select from list → "Aggiungi Celebrity" → save. System auto-counts. Only clearly identifiable, well-known celebrities should be entered; do not enter all models. |
| Mail Quotidiana — brand only | Only the brand name is entered. No sub-line, product, value, season. Pure brand detection. |
| Mail Quotidiana — placement rule | Insert brand on the page where the product is visually shown, not on the page with the caption. Caption can be on a different page (including at end of the article or end of the magazine). |
| Mail Quotidiana — brand scope | Narrower than EDI. Each group/publisher has a specific list of brands. Ralph Lauren example: "Ralph Lauren" at group level, not sub-brands like Purple Label separately. |
| Mail Quotidiana — system separation | Separate program from EDI/ADV system. No direct connection. What is entered in mail quotidiana is not visible in the EDI/ADV UI and vice versa (except via the PDF highlight export in Gestione Uscite). |
| OCR detection system | The OCR pipeline uses keyword lists to detect brand mentions. Limitations: keyword-based (primitive), only detects Western characters (fails on Russian/Cyrillic, Arabic, Japanese, Chinese, Korean), over-detects (designed to minimize omissions, not precision). The OCR pipeline is the base for both mail quotidiana and EDI pre-annotation. |

---

## 3. Pain Points

### A. Data Entry Complexity

| Pain Point | Impact |
|---|---|
| **Inserts require creating then deleting dummy pages** | Cumbersome; creates risk of leaving orphan records. Non-intuitive workflow for new operators. |
| **Campaign category assignment is inconsistent** | Same campaign visual inserted differently across operators (e.g., Chanel campaign sometimes entered as "borse", sometimes as "abbigliamento"). Silvana maintains a campaign reference file but it is not enforced at entry time. |
| **Gender in sub-lines** | Combined gender sub-lines (Abbigliamento Uomo/Donna) are ambiguous. Proposal to separate gender as a flag has been discussed but not implemented. Creates inconsistency in data. |
| **Season assignment for non-fashion categories** | Watches, jewellery, beauty have no obvious seasonal creative shift; operators apply magazine date rules inconsistently. Exact changeover dates are not documented — must be verified with Silvana. |
| **CoAdv / PTD grey areas** | No unambiguous rule for brand + retailer co-advertising. Clients dispute classification. Rule exists but is not always applied consistently. |
| **Celebrity entry requires searching a long list** | No significant new finding; confirms existing pain point. |

### B. Process / Procedure

| Pain Point | Impact |
|---|---|
| **No enforced cover/page-count ownership** | Either team can open an issue; whichever goes first must assign cover and run contapagine. If neither does it, downstream dependencies break. |
| **ADV closure requires manual click** | Operator must explicitly click "Terminato" to stamp the ADV closure date. Risk of forgetting. |
| **Campaign reference file not integrated into the tool** | Silvana's campaign-to-category mapping file exists externally; data entry operators cannot access it at the moment of entry. No enforcement mechanism. |
| **Season field not pre-populated** | Must be selected manually from dropdown every time. A rule-based pre-fill (derived from magazine issue date) has been proposed and validated as technically feasible by Alberto. Not yet implemented. |
| **Mail Quotidiana runs in a separate program** | Operators must switch contexts; data does not flow between programs. Prevents any cross-referencing during entry. |
| **OCR keyword list is unmaintainable** | Thousands of keywords; no multi-language support; false positives; designed for recall not precision. Not suitable as the foundation for AI-assisted automation. |

### C. Dependencies

| Pain Point | Impact |
|---|---|
| **Mail Quotidiana depends on OCR quality** | If OCR misses a brand mention (especially non-Western script), the operator has no alert and the brand will not appear in the daily report. |
| **Scan must be complete before ADV entry** | Confirms existing hard dependency. |
| **Caption-vs-product page placement requires visual judgment** | Operator must decide which page contains the product versus the caption. Cannot be reliably automated until caption detection is solved (see §4). |

---

## 4. Easily Automatable Opportunities

### Quick Wins (rule-based, no AI)

| Opportunity | Mechanism |
|---|---|
| **Pre-fill Season from magazine issue date** | Derive season from issue publication month using a lookup table (e.g., Dec–May → SS, Jun–Nov → AW). Pre-populate on record creation; operator confirms or overrides. Alberto has confirmed this is technically feasible. |
| **Integrate campaign reference file into data entry UI** | When operator selects a brand + magazine, display Silvana's campaign category mapping inline. Enforce or suggest the correct sub-line. Eliminates reliance on operator memory. |
| **Auto-stamp ADV closure** | Auto-trigger "Terminato" when all pages in the ADV queue have been processed, rather than requiring a manual click. Add a confirmation prompt to avoid accidental premature closure. |
| **Simplify insert creation** | Replace dummy-page creation with a direct "Create Insert" action that does not require temporary records to be deleted. |

### Medium-term (OCR / text extraction)

| Opportunity | Mechanism |
|---|---|
| **OCR: extend keyword detection to non-Western scripts** | Add Cyrillic, Arabic, CJK (Chinese/Japanese/Korean) brand name variants to the detection dictionary. Immediate coverage improvement for APAC and MENA titles. |
| **OCR: replace keyword matching with vision-based brand detection** | Use image recognition to detect brand logos and printed text rather than keyword lists. Higher precision, fewer false positives, language-agnostic. Prerequisite for reliable mail quotidiana and ADV automation. |
| **Caption detection (structural prerequisite for AI insertion)** | Identify caption text blocks vs. body text vs. image regions. Must reliably distinguish the page where a product is visually shown from the page containing the corresponding caption. **Francesca flags this as the primary blocker for AI-assisted ADV/EDI insertion.** Until this is solved, AI cannot correctly place brand records on the right page. |

### Longer-term (AI-assisted)

| Opportunity | Mechanism |
|---|---|
| **Mail Quotidiana: full automation for daily newspapers** | Newspapers have simpler methodology (fewer edge cases, values mostly mentions or 1/20th page). With improved OCR, brand detection on newspaper pages could be automated end-to-end with minimal human review. Francesca assesses this as achievable once OCR is improved. |
| **ADV campaign category pre-assignment via vision AI** | AI reviews campaign visual and proposes brand + sub-line assignment based on visual content (product type, visual style). Human confirms or overrides. Would replace the current manual reference-file lookup. |
| **Mail Quotidiana: magazine-level brand detection** | Once caption detection works reliably, AI can place brand records on the correct page (product-visible page, not caption page) for magazine issues as well as dailies. |

---

## 5. Strategic Takeaways

**ADV and EDI workflows are structurally parallel but operationally distinct.** Both use the same UI framework (Gestione Uscite, page-level and record-level entry) but ADV has fewer mandatory fields, different sub-lines (including gender variants), and a same-day delivery obligation (ADV veloci). These differences must be preserved in any automation design.

**Caption-vs-product page detection is Francesca's declared primary blocker.** She will not proceed with AI-assisted EDI or mail quotidiana development until this is demonstrably solved — not at development level but at test level ("smarcata a livello di test, non di sviluppo"). This must be the first AI capability to validate.

**OCR replacement / upgrade is the foundation layer.** Before automating either mail quotidiana or full EDI insertion, the brand detection layer (OCR) must be upgraded: multi-language support is the first priority. A working multilingual brand detector for mail quotidiana would also serve as the proof-of-concept for full EDI automation.

**Mail Quotidiana is the easiest automation target after OCR improvement.** The data model is simple (brand name only), the methodology is minimal, and the daily newspaper variant has very few edge cases. Francesca sees it as a natural first step after fixing OCR.

**Rule-based quick wins are desirable and uncontroversial.** Season pre-fill, campaign category enforcement, and ADV closure automation are small improvements that Francesca and Mariana both support. These should be implemented regardless of AI roadmap progress.

**Gender in sub-lines is a known structural issue.** Separating gender from product category into a dedicated flag/filter would improve consistency and simplify automation. Francesca supports this change; it is not yet scheduled.

**Co-advertising (CoAdv) is the most ambiguous classification in ADV.** Grey areas exist; client disputes occur. This will remain a human judgment call in the near term and should be excluded from automation scope.
