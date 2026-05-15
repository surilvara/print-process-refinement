# Print Data Entry (DMR) — Process Analysis

**Source:** Immersive session with Antonella Genovese, recorded by Mariana Martella — 14 April 2026

---

## 1. End-to-End Workflow (Actions) — Record-Level Data Entry

This session picks up where the previous session left off: from the page header onward, into the actual record-level data entry. The previous session documented the macro workflow (issue selection → page creation); this session documents what happens *inside* a page.

The operator follows this sequence for each page's editorial records:

1. **Open a page for data entry** — Use the magnifying glass icon (lentina) to enlarge the scanned image and read captions/credits. Pages are too small in the default thumbnail view to read page numbers or text.
2. **Create the page header** — Set Numero pagina, Facciata, Posizionamento. For special-positioning pages (e.g., Sommario), the lower fields (Servizio/Rubrica, Titolo, Tipo di testo) are not mandatory. Click **"Aggiungi"** to unlock the data entry form below. *Confirms existing knowledge.*
3. **Identify the first brand** — Open the brand dropdown. Brands appear alphabetically, numbers first. Type the first letters to filter. The dropdown shows brand + sector + sub-line combinations (e.g., "Christian Dior — Fashion", "Christian Dior — Gioielli", "Christian Dior — Occhiali"). **NEW:** These are not separate brands — they are the combination of brand + sector + category (sub-line), pre-filtered per brand.
4. **Select the sub-line (sottolinea)** — Type the first letters to narrow down. The sub-line encodes gender + product category (e.g., "Donna — Abbigliamento"). The sub-line structure is: `Gender — Category`.
5. **Search for product (if applicable)** — Use the magnifying glass icon to search products linked to that brand. Products exist mainly for jewellery, watches, bags, and shoes — not for general clothing. Product names are only entered if explicitly cited by the magazine (e.g., "Black Dress" by Saint Laurent). **NEW:** Operators must never start from the product field — always start from the brand. Some "free products" still exist in the system but may be linked to wrong brands; starting from product risks misattribution.
6. **Set Quantità** — Default is 1 (single page). Change to 2 for double pages. This is a manual selection.
7. **Set Oggetti (objects)** — Default is 1. If the brand has multiple visible items on the page (e.g., 2 bags), manually increase. Object count 0 has a special meaning: it signals a mention-only record where the brand is cited but not given visual space.
8. **Set Valore/Spazio** — The proportional space the brand occupies. Subjective visual estimation. **NEW detail on Sommario:** The Sommario (TOC) page photo is capped at a maximum value of 1/10 of a page, regardless of actual photo size. Multiple items within the TOC photo share this 1/10 (e.g., 2 items → 1/20 each).
9. **Set Stagione (season)** — Determined by publication cover date, not by article content. Season changes twice a year: P/E (Spring/Summer) for issues from February through July; A/I (Autumn/Winter) for issues from August through January. **NEW:** Only the current and future seasons are selectable. Past seasons cannot be used. If a magazine features a vintage or past-season item, the operator uses the current season + the sub-line "Collezioni passate" (Past Collections). Exception: items explicitly labeled as "vintage" (defined as 20+ years old) get the correct sub-line but no season at all.
10. **Set Tipo di comunicazione** — Select from dropdown. **NEW — full classification documented:**

    | Type | Sector | When to use |
    |---|---|---|
    | **Indossato** (Worn) | Fashion + Beauty | Product is worn by a model AND the specific product is described/credited |
    | **Indossato Marchio** (Worn Brand) | Beauty only | Caption says "Make-up: [Brand]" without specifying the exact product |
    | **Make-up Artist** | Beauty only | Caption credits a make-up artist by name, with or without product detail |
    | **Foto prodotto** (Product photo) | Fashion + Beauty | Product shown as a standalone image, not worn |
    | **Articolo** (Article) | Fashion + Beauty | Brand mentioned in text only, no image |
    | **Credit Fashion** | Fashion only | Brand listed in a fashion credit block (usually end-of-service), but impossible to attribute to a specific page/photo because credits are aggregated |

    **NEW — Credit Fashion logic:** When a fashion story has all credits grouped at the end (e.g., "Claudia Schiffer wears: Armani, Cucinelli, Ferragamo"), and it's impossible to determine which brand appears on which page, all brands receive a "Credit Fashion" entry with no space value — because the operator cannot attribute space to a brand they can't visually locate.
    
    **NEW — Exception to Credit Fashion:** If among grouped credits, one brand is the only representative of its product category (e.g., Manolo Blahnik is the only shoe brand), the operator *may* assign it space, because the reader can reasonably identify it. However, this is inconsistent and somewhat arbitrary.

11. **Set Celebrity flag + name** — If a celebrity is depicted (not just mentioned): tick the "Cel" flag (which indicates "person in pose") AND type the celebrity name in the name field below. If the celebrity is not in the database, the operator creates them. **NEW:** ~15 new celebrity entries are created per day. There is debate about criteria — e.g., minor politicians may not warrant celebrity status, but operators currently have unrestricted creation ability.

12. **Set additional flags if applicable:**
    - **Mono** — Monography flag
    - **TL** — Total Look flag
    - **FSA** — Fashion Show flag
    - **PR** — Pubblico Redazionale (advertorial) flag
    - **Bridal Product** — Used for jewellery/products featured in wedding specials

13. **Set Marchio Commercializzato (Sold Brand)** — **NEW — full rule documented:** When a product is featured alongside the retailer that sells it (e.g., "Dior lipstick available at Sephora"), a special "sold brand" rule applies:
    - Insert the product brand (Dior) normally with full details
    - Duplicate the record, change the brand to the retailer (Sephora), keep all other fields identical (same sub-line, same value, same tipo di comunicazione)
    - In the "Marchio Commercializzato" field on the retailer's record, select the product brand (Dior)
    - The retailer gets the same space value as the product brand — this rule was introduced by France to stop retailers being penalized with only Mentions
    - **NEW:** The Marchio Commercializzato dropdown pulls from the main brand database. If a brand doesn't exist (e.g., a non-client brand like "Catrice"), it gets created as a brand specifically for this purpose — this is why many brands exist in the system that are not client brands.

14. **Set Redattore / Fotografo / Agenzia** — Free-text fields for editorial credits.
    - **Format:** First name initial + period + full surname (e.g., "A.Genovese")
    - **Separator:** Semicolon between entries
    - **Agencies:** Written in full (e.g., "Getty Images")
    - Only one entry per category (if 2 photographers are credited, take the first one listed)
    - **NEW:** "Stylist" counts as the "Redattore" for fashion stories. If a ticket complains about missing editor on a fashion service, the stylist name is the correct entry.

15. **Set Contesto fields (Pagine Contesto, Prodotti Contesto)** — Used for contextualized articles. **NEW — full mechanism documented:**
    - When an article has a dominant theme (e.g., sun creams) with text pages + product pages, all pages are pooled together
    - Total space is divided equally among all products, giving them higher individual value than they'd get on their standalone pages
    - If a product appears 3× larger than others in the photo, it counts 3× (proportional weighting within the contextualized pool)
    - **Critical interaction:** Brands mentioned in the text of a contextualized article that also appear as products — they get Mention with Object 0 (no additional space), because their space is already counted in the contextualized pool
    - Brands in the text that are NOT among the products — they get their actual text space (e.g., 1/10), AND this space is subtracted from the total contextualized page count (e.g., 4 pages → 3.8 pages) to avoid double-counting

16. **Save the record** — Click "Aggiungi". The record appears in the bottom section of the page. A blue line indicates an editorial record (red = ADV).

17. **Edit/Delete/Duplicate** — 
    - Click the **X** to delete a record (deletions are NOT tracked in the audit log)
    - Click the **duplicate icon** to copy all fields to a new record — then change only the brand or sub-line. Major time-saver for pages with multiple similar items.
    - Click on a record in the bottom section to re-load it into the form above for editing
    - **NEW:** All modifications ARE tracked via the clock icon (orologio) — showing who, what, when. Only deletions are untraceable.

18. **Data visibility to clients** — Data syncs to Discover twice daily: at noon and after 18:00. No manual "close" action is needed. **NEW:** There is no need to close the editorial entry (chiusura EDI) for data to flow — any saved record is automatically included in the next sync.

---

## 2. Key Points

| Area | Detail |
|---|---|
| **Brand hierarchy** | What appears as "brands" in the dropdown is actually the combination of Brand + Sector + Sub-line. Major clients (e.g., Dior) have their brands split by sector (Fashion, Eyewear, Beauty, Jewellery), each as a separate selectable entry. Smaller clients have everything under one brand. |
| **Sub-line filters** | Filters restrict which sub-lines appear under a brand — e.g., under "Christian Dior Fashion", only fashion-related sub-lines are available (no eyewear, no make-up). This prevents operators from accidentally putting eyewear data under the fashion brand. Managed via Anagrafiche → Marchi. |
| **Filter management** | Filters are set by Antonella and Alberto via Web Digital (Anagrafiche → Marchi → search brand → Sottolinee). Historically done by default for major clients. Account managers may still have access to modify filters but typically don't. |
| **Brand split requests** | Creating separate brand entries per sector (e.g., "N°21 Eyewear" vs "N°21 Fashion") only happens when explicitly requested by the account team based on client instructions. Operators never initiate this on their own, even if they discover the information independently. |
| **Production companies** | Brand splits often relate to different production/licensing companies (e.g., Luxottica for eyewear, L'Oréal for beauty). The system needs to reflect which holding/production company receives data. When corporate changes happen (e.g., L'Oréal acquires Marc Jacobs beauty), Antonella may informally alert account managers, but formal brand restructuring requires account team action. |
| **Mandatory vs optional fields** | Brand, Sub-line, and Valore are mandatory (system blocks save without them). Stagione, Tipo di comunicazione, and Prodotto are technically optional — the system allows saving without them. However, current rules require Tipo di comunicazione on all records (historical exception: some Italian sectors like furniture/tourism previously didn't require it). |
| **Page creation logic** | Pages are only created when they contain data. Blank pages (no editorial content) are skipped — not even created as empty entries. Page numbering follows the magazine's own numbering even with gaps. |
| **Processing order** | Operators must follow the magazine page order sequentially. Jumping to known data-rich sections (e.g., going straight to the fashion story) is explicitly prohibited, because clients may open tickets asking why a brand appearing on page 20 (outside the fashion story) was not entered. The only exception: the Sommario is typically done last, because its cover image credits often depend on seeing the full magazine first. |
| **Unused fields** | "Designer", "Eliminazione", and "Note" fields in the data entry form are not used by the data entry team. Designer was possibly created for furniture data; Eliminazione is an account-level feature for removing specific brand records; Note has never been used. |
| **Audit trail** | Modifications are fully logged (who, what, when) via the clock icon. However, record deletions leave no trace. |

---

## 3. Pain Points

### A. Data Entry Complexity

| # | Pain Point | Impact |
|---|---|---|
| 1 | **Brand dropdown is a combined Brand+Sector+Sub-line list** — operators must navigate a very long alphabetized list that mixes brands with their sector variants. | Confirms existing (brand search from huge list). **NEW detail:** The list includes non-client "ghost" brands created solely for Marchio Commercializzato purposes, further inflating its size. |
| 2 | **Product field is brand-linked but includes legacy "free products"** — some products exist unlinked or linked to wrong brands. Operators must always start from brand, never from product. | **NEW.** Risk of misattribution if workflow is not followed. |
| 3 | **Credit Fashion forces arbitrary decisions** — when credits are grouped at end of story, operators cannot assign space. But if one brand is the sole representative of a category (e.g., only shoe brand), it *may* get space. The criteria for this exception are subjective. | **NEW.** Inconsistency between operators, potential client complaints. |
| 4 | **Contextualization calculation is complex** — pooling pages, proportional weighting, subtracting text-brand space from the pool. Requires fraction arithmetic under time pressure. | **NEW.** High cognitive load, error-prone. Confirms existing (value/space estimation is subjective), but adds a whole new dimension of complexity. |
| 5 | **Celebrity creation is unrestricted** — ~15 new entries/day with no gatekeeping on who qualifies as a celebrity. Minor politicians, local figures get created alongside global stars. | **NEW.** Database bloat, inconsistent standards across teams. |
| 6 | **Tipo di comunicazione has subtle distinctions** — Indossato vs Indossato Marchio vs Make-up Artist depends on whether the specific product, only the brand, or the make-up artist is named. Easy to confuse. | Confirms existing (service-type classification ambiguity), with **NEW** granular detail on the beauty-specific subtypes. |
| 7 | **Season assignment requires calendar awareness** — operators must know the biannual season calendar and apply it based on issue cover date, not article content. Vintage/past-collection items require workaround via sub-line. | **NEW.** Not previously documented at this level of detail. |

### B. Process / Procedure

| # | Pain Point | Impact |
|---|---|---|
| 8 | **Marchio Commercializzato requires full record duplication** — for every retailer mention alongside a product brand, the operator must duplicate the entire record, change the brand, and set the Sold Brand field. Doubles the work for common retail-cited products. | **NEW.** Significant time cost, especially in beauty/fragrance pages that frequently cite Sephora, Douglas, etc. |
| 9 | **Brand filter management is manual and ad-hoc** — filters are applied brand-by-brand by Antonella/Alberto. No systematic mapping exists. Filters are sometimes discovered to be wrong only when incorrect data surfaces. | **NEW.** No documentation or audit of which brands have which filters. Risk of silent misclassification. |
| 10 | **Corporate ownership changes are not systematically communicated** — when production/licensing companies change (e.g., L'Oréal acquires a brand's beauty line), there is no formal notification channel from account to DMR. Antonella sometimes catches it from press coverage in daily newspapers. | **NEW.** Data may flow to wrong holding company for extended periods. |
| 11 | **Deletions are untraceable** — while edits have full audit trail, deleted records leave no log. | **NEW.** Quality control cannot detect deleted data; potential for silent data loss. |

### C. Dependencies on Other Teams

| # | Pain Point | Impact |
|---|---|---|
| 12 | **Account team controls brand structure** — operators cannot create brand splits, modify sector assignments, or restructure brands without explicit account team request, even when they identify the need. | **NEW.** Delays in reflecting corporate changes; operators must wait for instructions they know are needed. |
| 13 | **Celebrity database has no central governance** — any operator can create any celebrity, but there are no clear criteria or approval workflow. | **NEW.** Quality and consistency depend on individual operator judgment. |

---

## 4. Easily Automatable Opportunities

### Quick wins (rule-based, no AI needed)

| # | Opportunity | How |
|---|---|---|
| A | **Auto-duplicate for Marchio Commercializzato** | When an operator marks a record with a Sold Brand, auto-generate the mirror record (swap brand, copy all other fields, set the commercializzato reference). Currently 100% manual duplication. |
| B | **Default season pre-fill based on issue cover date** | Issue cover date is known at the Gestione Uscite level. Auto-compute and pre-fill P/E or A/I based on the February–July / August–January rule. Operator overrides only for future-season exceptions. |
| C | **Sommario value cap enforcement** | Auto-cap all records on Sommario pages to max 1/10 total. If the operator enters values that exceed 1/10 in aggregate, warn or auto-adjust. |
| D | **Brand filter audit report** | Generate a report of all brands with their current sub-line filters. Expose brands with no filters or with possibly incorrect filters. No AI needed — pure database query. |

### Medium-term (OCR + text extraction)

| # | Opportunity | How |
|---|---|---|
| E | **Credit block parsing** | OCR the credit block at the end of fashion stories. Extract brand names and match against the brand database. Pre-populate Credit Fashion records for all identified brands. |
| F | **Retailer/Sold-Brand detection** | OCR product captions for patterns like "disponibile da/available at [retailer]" or "chez [retailer]". Auto-flag the record for Marchio Commercializzato treatment and suggest the retailer name. |
| G | **Celebrity name extraction with existence check** | OCR + NER to extract names, cross-reference against existing celebrity database. If found → pre-fill. If not found → flag for operator to confirm creation. Reduces the ~15/day blind creation rate. |

### Longer-term (AI-assisted)

| # | Opportunity | How |
|---|---|---|
| H | **Tipo di comunicazione suggestion** | Based on page layout analysis (is the product worn? is it a standalone shot? is it text-only?), suggest the correct communication type. Particularly valuable for the Indossato/Indossato Marchio/Make-up Artist distinction in beauty. |
| I | **Contextualization assistant** | Given a set of pages flagged as a contextualized article, auto-calculate the pooled page count, distribute value proportionally, identify text-only brands for Mention treatment, and compute the adjusted pool after text-brand subtraction. Present to operator for validation. |
| J | **Corporate change monitoring** | Monitor news feeds/press for brand ownership changes (acquisitions, licensing deals) and alert account managers proactively. Prevents the current situation where months pass before brand structures are updated. |

---

## 5. Strategic Takeaways from the Discussion

- **The record-level workflow is where the real complexity lives.** The previous session documented macro-level workflow (issue management, page creation). This session reveals that the cognitive load is concentrated in the data entry form itself: choosing the right brand+sub-line combination, applying space values, handling the Tipo di comunicazione matrix, and managing contextualization arithmetic. These are the areas where automation would have the highest impact per minute saved.

- **The Marchio Commercializzato rule is a hidden time multiplier.** Every product page that mentions a retailer effectively doubles the data entry work. This rule was introduced by France and applies globally. The duplication is entirely manual and a prime candidate for automation.

- **Brand filter governance is a systemic risk.** There is no documented map of which brands have which filters, no audit trail for filter changes, and no formal handoff between account managers and the DMR team. Filter errors surface only when incorrect data is noticed downstream — often by clients.

- **The celebrity database is growing uncontrolled.** At ~15 new entries per day with no approval workflow, the database will accumulate noise rapidly. This has downstream quality implications for Discover and client reporting.

- **Several "optional" fields are operationally mandatory.** The system was designed when Italy and international markets had different rules. Fields like Tipo di comunicazione are technically optional at database level but required by current methodology. This mismatch between system constraints and operational rules creates a category of errors the system cannot prevent.

- **Contextualization is the most complex calculation in the entire workflow.** It involves pooling pages, proportional weighting, handling brands that appear both as products and in text, and subtracting text space from the pool. This is a strong candidate for tool-assisted calculation, even without full automation.

- **Deletions being untraceable is a quality blind spot.** Modifications have full audit trail, but a deleted record simply disappears. This means quality control cannot distinguish between "data was never entered" and "data was entered and then deleted."
