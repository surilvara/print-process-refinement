# Print Data Entry (DMR) — Process Analysis

**Sources:**
- Session 1: Antonella Genovese & Francesca Boattini, recorded by Mariana Martella (issue-level workflow)
- Session 2: Antonella Genovese, recorded by Mariana Martella — 14 April 2026 (record-level data entry)
- Session 4: Francesca Boattini & Mariana Martella — approx. 17 April 2026 (ADV insertion + Mail Quotidiana)
- Session 6: Alberto Tornielli, Suril Vara, Mariana Martella — 5 May 2026 (OCR pipeline architecture & open-source evaluation)
- Session 7: Antonella Genovese, Francesca Boattini, Mariana Martella — 5 May 2026 (OCR renewal direction, Japan/Korea alignment, LVMH custom score)

---

## 1. End-to-End Workflow (Actions)

### Phase A — Issue-Level Workflow

The data entry operator follows this sequence for each magazine issue:

1. **Navigate to "Inserimento Dati"** → **"Gestione Uscite"** (Issue Management).
2. **Select country** (e.g., Italy) — this filters the relevant publication list.
3. **Consult the priority file (Scadenza Testate)** — this is a dynamic deadline matrix managed under *Anagrafiche → Scadenza Testate* in Web Digital. It works as follows:
   - Publications are grouped into **country groups** (e.g., Group A = Italy only, with tighter deadlines; other groups cover remaining countries). Currently 4 groups exist, but they are fully configurable.
   - Within each group, deadlines differ by **periodicity** (daily vs. non-daily) and by **priority tier** (P1, P2, P3).
   - For each combination, a **maximum number of calendar days** is set (e.g., P1 Italy = 7–10 days from arrival; P1 for other main countries may differ).
   - A separate rule governs the **monthly closing deadline** per priority tier.
   - The matrix combines all these parameters and computes a **per-issue deadline date** (the last column in the file). Issues are sorted by this date; when it passes, the row turns **red**.
   - There is also a fixed end-of-month rule to close all remaining items.
   - The file is owned and editable only by Francesca; operators consume it read-only. Changing the matrix (e.g., reducing P1 to 3 days) automatically recalculates all deadlines.
   - Team leads use the file each morning to assign operators: some on overdue/red items, others on newly arrived P1s. P1 deadlines and previous-month spillover constantly intersect.
4. **Select the publication and issue** — e.g., *Elle Italia*, April 2026.
5. **Verify the issue is ready** — the **"Fine Scansione"** (scan complete) flag must be present; without it, the operator is locked out. The issue must have been physically received, registered (arrival date + source logged), and fully scanned.
6. **Enter the issue** — click the **EDI** button (for editorial data entry) or the **ADV** button (for advertising data entry). Roles are enforced at user level: editorial operators only see EDI, ADV operators only see ADV.
7. **Set the cover image** — always named "C1", facciata = destra (right), positioning = "Prima di copertina". Click **"Imposta come immagine di copertina"** to generate the yellow frame. This associates the cover thumbnail with every record in the issue.
8. **For each page, click the pencil icon** and fill in the page header fields. For **regular editorial pages (rubriche/servizi)** all 6 fields are **mandatory**:
   - **Numero pagina** — page number (typed manually)
   - **Facciata** — left (sinistra) / right (destra) / double (doppia)
   - **Posizionamento** — single page (singola) / double page (doppia) / or a special-positioning value
   - **Servizio / Rubrica** — section or service name
   - **Titolo** — article title
   - **Tipo di testo** — text type
   For **special-positioning pages** (cover, sommario, staff, editoriale, indirizzi), only the top section is required: Numero pagina, Facciata, and the special Posizionamento value. The lower fields (Servizio/Rubrica, Titolo, Tipo di testo) are **not mandatory** because these pages are not editorial content.
9. **Save the page header** → the system unlocks the full data-entry form for that page.
10. **Repeat** for every page in the issue, then move to the next issue following the priority file order.

**Important rules:**
- Pages are only created when they contain data. Blank pages are skipped entirely.
- Operators must follow page order sequentially. Jumping to known data-rich sections is prohibited — clients may open tickets for missed data on skipped pages.
- Exception: the Sommario is typically entered last, because its cover image credits often depend on having seen the full magazine first.

### Phase B — Record-Level Data Entry (per page)

Once a page header is saved and the data-entry form is unlocked, the operator enters one record per brand per page:

1. **Enlarge the scanned image** — use the magnifying glass (lentina) to read captions and credits. Default thumbnails are too small.
2. **Select Brand** — open the brand dropdown and type the first letters. The dropdown shows brand + sector + sub-line combinations (e.g., "Christian Dior — Fashion", "Christian Dior — Gioielli"). Major clients have brands split by sector; smaller clients have everything under one brand. Always start from the brand, never from the product.
3. **Select Sottolinea (sub-line)** — type the first letters. Encodes gender + category (e.g., "Donna — Abbigliamento"). Sub-lines are filtered per brand via configurable filters (Anagrafiche → Marchi → Sottolinee) to prevent errors.
4. **Search Product (if applicable)** — use the magnifying glass to search products linked to the brand. Products exist mainly for jewellery, watches, bags, and shoes. Only enter if the magazine explicitly names the product.
5. **Set Quantità** — 1 for single page (default), 2 for double page.
6. **Set Oggetti (objects)** — default 1. Increase for multiple visible items of the same brand. Object 0 = mention-only (brand cited but no visual space assigned).
7. **Set Valore/Spazio** — proportional space the brand occupies. Subjective visual estimation. Special rule: Sommario photos are capped at max 1/10 of a page.
8. **Set Stagione** — determined by issue cover date: P/E (Spring/Summer) for Feb–Jul issues; A/I (Autumn/Winter) for Aug–Jan. Only current and future seasons are selectable. For past-season items, use current season + sub-line "Collezioni passate". For vintage items (20+ years old), use correct sub-line but no season.
9. **Set Tipo di comunicazione:**

   | Type | Sector | When to use |
   |---|---|---|
   | **Indossato** | Fashion + Beauty | Product is worn AND the specific product is described |
   | **Indossato Marchio** | Beauty only | Caption says "Make-up: [Brand]" without specifying product |
   | **Make-up Artist** | Beauty only | Caption credits a make-up artist by name |
   | **Foto prodotto** | Fashion + Beauty | Product shown as standalone image, not worn |
   | **Articolo** | Fashion + Beauty | Brand mentioned in text only, no image |
   | **Credit Fashion** | Fashion only | Brand listed in aggregated credits (e.g., end-of-service block), impossible to attribute to specific page |

10. **Set Celebrity flag + name** — if celebrity is depicted: tick "Cel" flag AND type name. If not in database, create. Format: first initial + period + surname (e.g., "C.Cottin").
11. **Set additional flags** — Mono (monography), TL (total look), FSA (fashion show), PR (pubblico redazionale), Bridal Product (wedding specials).
12. **Set Marchio Commercializzato** — if a retailer is cited alongside the product brand (e.g., "Dior lipstick at Sephora"): duplicate the record, change brand to retailer, keep all other fields identical, and set the Marchio Commercializzato field to the product brand. Both get the same space value.
13. **Set Redattore / Fotografo / Agenzia** — format: initial.Surname (e.g., "A.Genovese"); semicolon separator; agencies written in full. One entry per category; if multiple, take the first listed. Stylist = Redattore for fashion stories.
14. **Set Contesto fields** — for contextualized articles: pool all pages of the themed article, divide total space equally among products (with proportional weighting for size differences). Brands in text that are also products → Mention with Object 0. Brands in text that are not products → get their text space, subtracted from the pool total.
15. **Click "Aggiungi"** to save the record. Blue line = editorial (EDI). Red line = advertising (ADV).
16. **Edit/Delete/Duplicate** — X to delete (untraced), duplicate icon to copy all fields (then change brand), click record to re-edit. Modifications are logged via clock icon (who, what, when). Deletions leave no audit trail.
17. **Data syncs to Discover twice daily** — at noon and after 18:00. No manual close action needed.

---

### Phase C — ADV (Advertising) Data Entry Workflow [Updated: 2026-04]

The ADV workflow shares the same Gestione Uscite framework but operates in a parallel lane from EDI. Key structural difference: ADV must be completed **the same day the magazine is published** (to feed the ADV veloci publisher reports). This creates pressure to start early — ADV operators often enter before the editorial team.

**Cover + contapagine ownership:** There is no fixed rule. Whichever team (ADV or EDI) opens the issue first must assign the cover image and run the page count (contapagine). The second team finds it already done.

**Page-level fields (mandatory for every ADV page):**
1. Numero pagina
2. Facciata (sinistra / destra / doppia)
3. Posizionamento
4. Formato (page size — uses the same scale as editorial)
5. Image (optional: attach scanned image to the page)

**Insert handling (additional page-level step when applicable):**
- If the page belongs to an insert, click "Associa Inserto" to link it to an insert record.
- To create a new insert record: create temporary dummy pages, fill in insert metadata (tipo, format, brand, description), save the insert, then delete the dummy pages.
- Insert format field: expressed as multiplier × pages (e.g. "1×2" for a 2-page gatefold, "1/3" for a small-format booklet, "1×4" for a 4-page poster insert).
- **Biancavolta**: a specific insert type where both sides of a detachable page are advertising for the same brand. Always 2 pages; format = "1×2".
- **Valuation rule for inserts**: a loose (free-standing) insert of any number of pages = 1 full page. A bound insert inside the magazine = valued by occupied space (same scale as regular pages).

**Record-level fields:**

| Field | Notes |
|---|---|
| **Marchio** | Brand — mandatory |
| **Sottolinea** | Sub-line — mandatory. ADV sub-lines include gender variants not present in EDI: Abbigliamento Uomo, Abbigliamento Donna, Abbigliamento Uomo/Donna, Profumo Uomo, Profumo Donna, Profumo Uomo/Donna. If two different genders appear in one creative → use the combined sub-line. If two separate creatives → two records. |
| **Prodotto** | Product — if identifiable from the ad |
| **Quantità** | 1 for single page or two different creatives in a double. 2 for a double page with the same creative. |
| **Valore/Spazio** | Same dropdown as editorial. ADV formats: full page, half page (horizontal or vertical), quarter, third. Rare in magazines; more common in dailies. |
| **Stagione** | Season of the **campaign**, not the magazine issue. For fashion sub-lines: infer from creative visuals. For watches/jewellery/accessories with no obvious seasonal signal: follow publication month (approx. Dec–May = SS, Jun–Nov = AW). Exact changeover dates: verify with Silvana. |
| **Campione Prodotto** | Flag for physical samples attached to the page: banda profumata, sample, tessera, cartolina. Relevant only for publisher reports (ADV veloci); no impact on MIV. Usage has declined — once very common for fragrances. |
| **PR flag** | Publiredazionale: ad that looks like editorial. Can be identified and flagged by either ADV or EDI team. Always counts as ADV in client analysis. Rule: use minimum number of sub-lines (typically 1). |
| **Bridal Product** | Same flag as in EDI; flags wedding-specific products. |
| **CoAdv / PTD** | Co-advertising flag: ad paid by two parties (brand + retailer, or two brands). The cost split is implicit from having two records on the same page; the flag is additional metadata for filtering. Grey area: clients sometimes dispute classification. Not suitable for automation. |
| **Regalo con Acquisto** | Gift-with-purchase flag: ad explicitly offering a free gift for a purchase. |
| **Posizione in pagina** | Small-format position within the page (finestrella, banner, box, piedino). Used primarily for daily newspapers; rare in magazines. For publisher reports. |
| **Celebrity** | Search by first letters → select from list → "Aggiungi Celebrity" → save. System counts automatically. Only clearly identifiable, well-known celebrities; do not enter all models. |
| **Codice eliminazione** | Set by account managers only; not a data entry field. |

**Multi-record rules for ADV pages:**
- Same double-page spread, **one creative** → 1 record, quantità = 2
- Same double-page spread, **two different creatives (same brand)** → 2 records, quantità = 1 each, value = full page each
- Example: a double page with orologio A on the left and orologio B (different model) on the right → 2 records, one per model

**ADV closure:**
After all ADV pages for an issue are entered, the operator must manually click **"Terminato" / "Fine Inserimento ADV"**. This stamps the ADV closure date, which becomes visible in Gestione Uscite. It is not triggered automatically.

---

### Phase D — Mail Quotidiana Workflow [Updated: 2026-04]

Mail Quotidiana is a **separate program** from the main EDI/ADV system. The two systems are not connected — data entered in one is not visible in the other (except via PDF highlight export).

**Purpose:** A daily anticipation service that sends basic brand-presence data to publisher clients for a specific list of titles. Entry is brand-name-only; no methodology, no values, no sub-lines.

**Workflow:**
1. When a physical magazine arrives, its arrival is registered. This populates the Mail Quotidiana queue.
2. Open the Mail Quotidiana program → select country → select publication → select date/issue.
3. A vertical gallery of page pairs loads (cover alone on right, then all pages paired left-right).
4. An internal link button between each pair allows the operator to confirm or break double-page associations.
5. Click on any page → a simplified entry mask opens.
6. Enter **only the brand name(s)** present on that page.
7. **Critical placement rule:** enter the brand on the page where the product is **visually shown**, NOT on the page containing the caption or credits (which may appear on a different or later page — sometimes at the end of the service, sometimes at the end of the magazine).
8. The system generates a highlighted PDF for monitoring: one version marks only the brands in the publisher's mail quotidiana scope; a separate version marks all EDI-scope brands.

**Brand scope:**
- Narrower than EDI. Each publisher group manages its own list of brands. Not all brands tracked in EDI have mail quotidiana coverage.
- Groups are managed within the program: each group has recipient email addresses + associated brand list.
- Sub-brand granularity is lower than EDI (e.g., "Ralph Lauren" as a group, not "Ralph Lauren Purple Label" separately).

**OCR dependency:** [Updated: 2026-05]
The mail quotidiana operator's brand detection is assisted by the DMR OCR pipeline. See §6 OCR Pipeline below for full architecture. Pipeline limitations that directly affect mail quotidiana quality:
- **Brand identification is keyword/alias-based**, not vision-based: prone to false positives, designed for recall (minimize omissions) over precision.
- **Western-script bias**: the alias dictionary contains predominantly Latin character entries — misses brands written in Cyrillic, Arabic, Chinese, Japanese, Korean.
- **Multi-column layout breaks brand matching**: when a brand name is split across two columns (e.g., "Van Cleef" with "Van" in one column and "Cleef" in the next), Google Vision parses them as separate blocks and the alias matcher fails. This is the dominant failure mode on newspapers.

**Automation outlook (per Francesca Boattini):**
- Mail Quotidiana for **daily newspapers** is the most feasible near-term automation target: simpler methodology, fewer edge cases, values mostly mentions or 1/20th page.
- For **magazines**: automation is blocked until caption detection is solved (see §4 for the caption-vs-product placement rule).
- Improving OCR brand detection to cover non-Western scripts is the first and most impactful prerequisite for both mail quotidiana and EDI automation.

---

### Glossary of Actions, Fields & System Terms

| Term | Type | Description |
|---|---|---|
| **Web Digital** | System | The main platform used for all print data entry operations. |
| **Inserimento Dati** | Navigation | Top toolbar menu item to access the data entry area. |
| **Gestione Uscite** | Screen | The issue management view — lists all issues by country, with filters for status and priority. |
| **Crea Report** | Action | Generates the list of all issues (dailies + magazines) for the selected country and date range. |
| **Crea Uscita Presunta** | Action | Creates a presumed (expected) future issue based on the publication's known periodicity. Pre-fills cover date by incrementing the last issue's date. |
| **Scadenza Testate** | Config (under Anagrafiche) | The deadline matrix that computes per-issue deadlines from country group, periodicity, and priority tier. |
| **Fine Scansione** | Status flag | Indicates the physical magazine has been fully scanned and images are ready. Required before any data entry can begin. |
| **Arrivato** | Status flag | A check mark indicating the physical copy has been received and registered (arrival date + source). |
| **EDI** | Button / Role | Opens the editorial data-entry view. Only visible to operators with the editorial role. |
| **ADV** | Button / Role | Opens the advertising data-entry view. Only visible to operators with the ADV role. |
| **Imposta come immagine di copertina** | Action | Assigns the selected page image as the issue's cover. Generates a yellow border and propagates the thumbnail to all records. |
| **Numero pagina** | Field | The page number. Typed manually; must match the printed number on the page. |
| **Facciata** | Field (dropdown) | Page orientation: Sinistra (left), Destra (right), or Doppia (double spread). |
| **Posizionamento** | Field (dropdown) | Page type: Singola (single), Doppia (double), or special values — Prima di copertina, Sommario, Editoriale, Staff, Indirizzi. |
| **Servizio / Rubrica** | Field | The editorial section or service name (e.g., "Cover Look", "Moda", "Beauty"). Mandatory for regular pages only. |
| **Titolo** | Field | Article or feature title. Mandatory for regular pages only. |
| **Tipo di testo** | Field | Text classification. Mandatory for regular pages only. |
| **C1, C2, C1a, C1b…** | Naming convention | Cover page identifiers. C1 = front cover, C2 = inside front cover. Multi-cover issues use alphabetical suffixes (C1a, C1b, C1c…). |
| **R1** | Naming convention | First editorial page after the cover section. |
| **I + progressive** | Naming convention | Insert numbering for uncounted pages: last numbered page + "I" + sequential number (e.g., 9.I1, 9.I2, 9.I3). |
| **Collage** | Image type | A composite image created by the scanning team showing all covers of a multi-cover issue side by side. Becomes the C1 thumbnail. |
| **Priorità 1 / 2 / 3 (P1, P2, P3)** | Classification | Priority tiers assigned to each publication. P1 = highest urgency, shortest deadline. |
| **Indossato** | Flag / Tipo di comunicazione | "Worn" — product is worn by a person AND the specific product is described/credited. |
| **Indossato Marchio** | Tipo di comunicazione (Beauty only) | Caption credits the brand (e.g., "Make-up: Dior") without specifying the exact product. |
| **Make-up Artist** | Tipo di comunicazione (Beauty only) | Caption credits a make-up artist by name, associated with a brand. |
| **Foto prodotto** | Flag / Tipo di comunicazione | "Product photo" — product shown as a standalone image, not worn. Used across all sectors. |
| **Articolo** | Tipo di comunicazione | Brand mentioned in text only, no image. |
| **Credit Fashion** | Tipo di comunicazione (Fashion only) | Brand listed in an aggregated credit block (usually end-of-service), impossible to attribute to a specific page. |
| **Valore / Spazio** | Field | The proportional space a brand occupies on the page (e.g., 1/20, 1/15, 1/8, 1/6). |
| **Oggetti** | Field | Number of visible items of the brand on the page. Default 1. Object 0 = mention-only record (brand cited but no visual space). |
| **Quantità** | Field (dropdown) | Page count: 1 = single page (default), 2 = double page. |
| **Stagione** | Field | Season assigned to the record. Determined by issue cover date: P/E (Feb–Jul), A/I (Aug–Jan). Only current and future seasons selectable. |
| **Collezioni passate** | Sub-line | Special sub-line used when a past-season item is featured but past seasons are not selectable. Combined with current season. |
| **Sottolinea** | Field | Sub-line: the combination of gender + product category (e.g., "Donna — Abbigliamento"). Filtered per brand. |
| **Filtri (sub-line filters)** | Config (Anagrafiche → Marchi) | Configurable restrictions on which sub-lines are available per brand. Set by Antonella/Alberto to prevent classification errors. |
| **Marchio Commercializzato (Sold Brand)** | Field | When a retailer (e.g., Sephora) is cited alongside a product brand (e.g., Dior), the retailer record gets this field set to the product brand. Both receive the same space value. |
| **Aggiungi** | Button | Saves a record within a page. Must be clicked after all mandatory fields are filled. |
| **Duplica** | Action (icon) | Copies all fields of an existing record into a new one. Operator then changes only what differs (e.g., brand). Major time-saver. |
| **Orologio (clock icon)** | Audit | Shows modification history: who changed what, when. Note: record deletions are NOT logged. |
| **Lentina (magnifying glass)** | UI element | Enlarges the scanned page image for reading captions and credits. Also used to search products linked to a brand. |
| **Cel** | Flag | Celebrity flag — indicates a famous person is depicted (in pose) on the page. Must be accompanied by the celebrity name in the field below. |
| **Redattore / Fotografo / Agenzia** | Fields | Free-text editorial credits. Format: initial.Surname; semicolon separator; agencies in full. One entry per category. Stylist = Redattore for fashion. |
| **Pagine Contesto / Prodotti Contesto** | Fields | Used for contextualized articles. "Pagine Contesto" = total pooled pages; "Prodotti Contesto" = number of products in the pool. |

---

## 2. Key Points

| Area | Detail |
|---|---|
| **Priority system** | Three tiers (P1, P2, P3). P1 targets: 2–3 days. Deadlines are computed by a configurable matrix combining country group, daily-vs-magazine, and priority tier. Francesca owns the matrix. |
| **Deadline file** | Rows turn red when overdue. Team leads redistribute operators each morning: some on overdue items, others on incoming P1s. P1 deadlines and previous-month spillover constantly intersect. |
| **Presumed issues** | The system pre-creates future issues based on publication frequency (weekly → 4/month, monthly → 1, daily → ~30). This is semi-automatic — requires a manual click ("Crea uscita presunta"). |
| **Scan dependency** | No data entry can begin until the physical magazine is received, registered (arrival date + source), and scanned. This is a hard blocker. |
| **Role segregation** | EDI (editorial) and ADV (advertising) operators are separated by user role to prevent accidental cross-entry. |
| **Cover association** | Critical first step: the cover thumbnail propagates to every record in that issue across all DMR platforms. |
| **Page numbering** | Must match the printed number. When pages are unnumbered, operators count from C1. Uncounted inserts use a "last-numbered-page + I + progressive" convention (e.g., 9.1, 9.2). Printing errors or mid-magazine inserts with their own numbering restart via alphabetical suffixes (A, B, C…). |
| **Multiple covers** | Several scenarios: sequential covers in the same copy, rotational covers across print runs, subscription-only covers, digital covers. All are entered only if mentioned inside the magazine itself. Additional covers require a ticket to the scanning team. |
| **Methodology is uniform — but LVMH has a custom score** [Updated: 2026-05] | Same data-entry methodology rules apply across all brands and sectors — no client-specific methodology exists at the operator level. Differences in operational scope are only in the number of brands tracked per publisher (e.g., certain US publishers track all brands on 4 key titles). **However:** LVMH receives a **client-specific score computed via custom formulas** that depend on which methodology flags are applied to records. Some flags feed the LVMH formula, others do not. Operators don't change their workflow for LVMH, but any **rule or flag-taxonomy change** at the methodology level must be screened against the LVMH formula before adoption. See §5 takeaway and OQ-28. |
| **Campaign identification (ADV only)** | Relevant only to ADV data entry (not editorial). Operators used to receive campaign PDFs from clients (e.g., Valentino via Nadia/Frustaeci). This no longer happens — ADV teams now search campaigns on Modelcom independently, which is slower and more error-prone. |
| **Quality bar** | Print error tolerance is near zero (stated ~3%), far stricter than web/social. Clients (especially LVMH) rely on granular fields like "service type" to compute scores. |
| **Brand hierarchy in dropdown** | What appears as "brands" in the dropdown is the combination of Brand + Sector + Sub-line. Major clients (e.g., Dior) are split by sector (Fashion, Eyewear, Beauty, Jewellery), each as a separate entry. Smaller clients have one brand for all sectors. |
| **Sub-line filters** | Configurable restrictions (Anagrafiche → Marchi → Sottolinee) control which sub-lines appear per brand, preventing operators from placing data under wrong sectors. Managed by Antonella and Alberto. No documented map of filter configurations exists. |
| **Brand split governance** | Creating separate brand entries per sector (e.g., "N°21 Eyewear") only happens when explicitly requested by the account team. Operators never initiate, even if they discover the need independently. Splits often relate to different production/licensing companies (Luxottica for eyewear, L'Oréal for beauty). |
| **Mandatory vs optional fields** | Brand, Sub-line, and Valore are system-mandatory (block save). Stagione, Tipo di comunicazione, and Prodotto are technically optional at system level but required by current methodology. Historical exception: some Italian sectors previously didn't require Tipo di comunicazione. |
| **Page creation logic** | Pages are only created when they contain data. Blank pages are not entered. Processing must follow magazine page order — no jumping ahead. Exception: Sommario is done last. |
| **Marchio Commercializzato rule** | When a retailer is cited alongside a product brand, both get duplicate records with identical space values. Rule introduced by France. Creates non-client "ghost brands" in the database. |
| **Tipo di comunicazione taxonomy** | Six types: Indossato, Indossato Marchio (beauty only), Make-up Artist (beauty only), Foto prodotto, Articolo, Credit Fashion (fashion only). Critical distinction for scoring — especially for LVMH clients. |
| **Season calendar** | Biannual: P/E for Feb–Jul issues, A/I for Aug–Jan. Only current + future selectable. Past-season items → sub-line "Collezioni passate" + current season. Vintage (20+ years) → correct sub-line, no season. |
| **Audit trail** | Modifications fully logged (who, what, when) via clock icon. Deletions leave no trace — a quality blind spot. |
| **Data sync to Discover** | Records sync twice daily (noon + 18:00). No manual close/publish action required. |
| **Celebrity creation** | ~15 new entries created per day. Any operator can create. No approval workflow or gatekeeping criteria. Debate exists around whether minor figures (e.g., local politicians) qualify. |
| **Unused fields** | "Designer", "Eliminazione", and "Note" fields are not used by data entry. Designer was possibly for furniture; Eliminazione is account-level; Note has never been compiled. |

---

## 3. Pain Points

### A. Data Entry Complexity

| # | Pain Point | Impact |
|---|---|---|
| 1 | **Fully manual page-number entry** — operators type every page number, facciata, and positioning by hand. | Slow, error-prone, high repetition. |
| 2 | **Page-numbering anomalies** — uncounted pages, inserts, printing errors, mid-magazine supplements with their own numbering, Arabic right-to-left magazines. Every case requires manual judgment and ad-hoc renumbering conventions (I+progressive, alphabetical suffixes, "bis"). | High cognitive load, no system guidance. |
| 3 | **Brand search from a huge list** — operators scroll/search through hundreds of sub-lines to find the right brand + sub-brand + product line. | Major time sink on every single page. |
| 4 | **Celebrity names typed manually** — no auto-suggest; operators must type full names and verify they are depicted (not just mentioned). | Slow, inconsistent spelling. |
| 5 | **Value/space estimation is subjective** — assigning 1/20 vs. 1/15 vs. 1/8 of page space requires visual judgment with no measuring tool. | Inconsistency between operators. |
| 6 | **Service-type classification ambiguity** — distinguishing "beauty" from "fashion" service types is nuanced and critical (LVMH uses it for scoring), but rules are complex and exception-heavy. | Even experienced operators disagree; AI would struggle here too. |
| 7 | **No pre-population of any field** — every field starts blank on every page. | Enormous amount of repetitive typing. |
| 8 | **Tipo di comunicazione has subtle beauty-specific distinctions** — Indossato vs Indossato Marchio vs Make-up Artist depends on whether specific product, only brand, or make-up artist is named. Easy to confuse. | Inconsistency, especially for less experienced operators. |
| 9 | **Contextualization calculation is complex** — pooling pages, proportional weighting by product size, subtracting text-brand space from the pool. Requires fraction arithmetic under time pressure. | High cognitive load, error-prone. |
| 10 | **Credit Fashion forces arbitrary decisions** — grouped end-of-service credits cannot be attributed to specific pages. Exception: if a brand is the sole representative of its category, it *may* get space. Criteria are subjective. | Inconsistency between operators, potential client complaints. |
| 11 | **Season assignment requires calendar awareness** — biannual calendar, cover-date-based, with workarounds for past-season and vintage items. | Not intuitive for new operators. |
| 12 | **Celebrity creation is unrestricted** — ~15 new entries/day with no gatekeeping criteria. | Database bloat, inconsistent standards. |
| 13 | **Legacy "free products" in database** — some products exist unlinked or linked to wrong brands. Operators must always start from brand, never from product. | Risk of misattribution if workflow not followed. |

### B. Process / Procedure

| # | Pain Point | Impact |
|---|---|---|
| 14 | **Cover caption hunting** — cover credits may be in the summary, in the editorial, in a "Cover Look" section, in credits at the back, or inside a related fashion spread. No fixed location. | Operators often do the entire magazine first, then return to the cover — double handling. |
| 15 | **Multiple-cover detection** — operators must notice mentions of alternative covers inside the magazine, then open a ticket to scanning, attach proof, and wait for the collage image before entering data. | Multi-step manual process, easy to miss. |
| 16 | **Campaign identification without client input (ADV only)** — since clients no longer send campaign PDFs, ADV operators must independently determine which campaign an ad belongs to, often guessing between RTW, bags, beauty, etc. | Misclassification (e.g., "bags" campaign labeled as "RTW" or vice versa). |
| 17 | **Marchio Commercializzato requires full record duplication** — for every retailer cited alongside a product brand, the operator must duplicate the entire record, change the brand, and set the Sold Brand field. | Doubles work for common retail-cited products (Sephora, Douglas, etc.). |
| 18 | **Brand filter management is manual and ad-hoc** — filters applied brand-by-brand with no systematic map or audit trail. Errors discovered only when incorrect data surfaces. | Silent misclassification risk. |
| 19 | **Corporate ownership changes not systematically communicated** — no formal channel from account team to DMR for production/licensing changes. Antonella sometimes catches it from press. | Data may flow to wrong holding company for extended periods. |
| 20 | **Deletions are untraceable** — edits have full audit trail, but deleted records leave no log. | Quality control cannot detect silent data loss. |

### B. Process / Procedure — ADV-specific additions [Updated: 2026-04]

| # | Pain Point | Impact |
|---|---|---|
| 26 | **Cover/contapagine ownership is unassigned** — whichever team opens the issue first must do it, but there is no rule or enforcement. If both teams assume the other will handle it, neither assigns the cover. | Risk of missed cover association; dependency for all downstream records. |
| 27 | **ADV closure requires a manual click** — the operator must actively click "Terminato" after completing all ADV pages. It is not automatically triggered when the last page is entered. | Risk of forgetting to close; ADV closure date (used for publisher reports) may be absent or wrong. |
| 28 | **Insert creation requires dummy pages** — to register a new insert, operators must create temporary pages, fill in insert metadata, save, then delete the dummy pages. | Cumbersome, non-intuitive; risk of leaving orphan dummy records. |
| 29 | **Campaign category assignment is inconsistent** — same campaign visual inserted differently across operators (e.g., Chanel handbag campaign entered as "borse" by some, "abbigliamento" by others). Silvana maintains a reference mapping file externally, but it is not integrated into the system. | Classification inconsistency at scale; affects brand analysis quality. Confirms pain point #16. |
| 30 | **Gender sub-lines create ambiguity** — ADV sub-lines include combined gender variants (Abbigliamento Uomo/Donna, Profumo Uomo/Donna). The rule for applying these is clear but the taxonomy itself is inconsistent: gender is embedded in the sub-line rather than being a separate flag. | Complicates automation; complicates filtering by category without gender conflation. Francesca has long wanted to separate gender into a standalone flag. |
| 31 | **Season changeover dates are undocumented for ADV** — for non-fashion categories (watches, jewellery, accessories), the seasonal boundary is approximately December–May = SS, June–November = AW, but exact dates must be verified with Silvana. Not codified in any system or document. | New operators apply inconsistent season values; periodic correction campaigns needed. |
| 32 | **CoAdv (PTD) classification is contested** — clients sometimes dispute whether a brand + retailer co-presence constitutes CoAdv. No unambiguous rule; grey areas exist, especially for gift-with-purchase scenarios. | Manual judgment required; not automatable in near term. |
| 33 | **Caption placement rule for Mail Quotidiana is hard to automate** — the brand must be entered on the page where the product is visually shown, not the caption page. Captions can be on the facing page, at the end of the article, or at the end of the magazine. AI systems that read text will systematically insert the brand on the wrong (caption) page. | Primary blocker for AI-assisted mail quotidiana and EDI automation, per Francesca. Must be solved at test level before any AI development starts. |
| 34 | **OCR brand alias dictionary covers only Western scripts** [Updated: 2026-05] — the Stage 2 brand alias dictionary contains predominantly Latin character entries. Brands written in Cyrillic, Arabic, CJK scripts are largely invisible to the system. | Systematic omissions in APAC and MENA titles; mail quotidiana quality directly impacted. First priority for OCR improvement. |
| 35 | **Multi-column brand splits break Stage 2 matching** [Updated: 2026-05] — Google Vision splits text into blocks based on whitespace alone, with no semantic/layout understanding. When a multi-word brand name spans two columns (e.g., "Van" / "Cleef"), each fragment lands in a separate block and the alias matcher fails. | Dominant failure mode on newspapers and multi-column layouts. Single-word brands unaffected; multi-word brands (Patek Philippe, Van Cleef & Arpels, etc.) at risk. Heuristic column-merging logic exists but is unreliable. |
| 36 | **Google Vision is a non-trivial recurring cost** [Updated: 2026-05] — ~4M images/year processed through the commercial Google Vision API. | Material cost line. Open-source OCR alternatives are under evaluation (Suril) but no replacement has matched accuracy yet. Constraint: any replacement must produce bounding-box coordinates so Stage 2 matching and the operator-side yellow-highlight UI continue to work. |
| 37 | **Country-specific rule pools (Japan/Korea) may be defensively too narrow** [Updated: 2026-05] — the Japan/Korea structural-override logic is scoped to a named publication pool. Publications outside that pool that exhibit the same patterns (systematic Sponsored labels on editorial content) have no mechanism to receive the same treatment. | Risk of inconsistent classification for similar-behaving publications outside Japan/Korea. Cross-reference Session 5 + general-rules.md §6. |
| 38 | **Renewal scope ambiguity: incremental OCR vs. LLM rewrite** [Updated: 2026-05] — two parallel OCR-renewal directions are alive: (a) incremental enhancements on top of Google Vision (LLM reading-order, multilingual aliases, open-source benchmark — Session 6); (b) Margot/Pau's deeper LLM-direction Stage 2 rewrite (Session 7). Not yet reconciled into a single roadmap. | Risk of duplicated effort or misaligned investment. Mariana's open action: investigate the difference before commitment. |

### C. Dependencies on Other Teams

| # | Pain Point | Impact |
|---|---|---|
| 21 | **Scan dependency as a hard gate** — if scanning is delayed, operators are blocked with no workaround, even if the physical magazine is in hand. | Idle time, schedule compression downstream. |
| 22 | **Multi-cover collage depends on scanning team** — after the operator opens a ticket requesting additional covers, the scanning team must locate, scan, and assemble the collage image before data entry can proceed on those covers. | Waiting time, back-and-forth communication. |
| 23 | **Physical magazine reception depends on logistics** — arrival timing is outside the data entry team's control, especially for foreign publications that don't arrive daily (unlike Italian ones). Late arrivals compress all downstream deadlines. | Uneven workload, deadline pressure spikes. |
| 24 | **Account team controls brand structure** — operators cannot create brand splits or restructure brands without explicit account team request, even when they identify the need. | Delays in reflecting corporate changes. |
| 25 | **Celebrity database has no central governance** — any operator can create, no approval workflow. | Quality depends on individual judgment. |
| 26_lvmh | **LVMH custom score creates a hidden veto on methodology changes** [Updated: 2026-05] — LVMH receives a client-specific score computed via custom formulas. Some methodology flags feed the formula, others do not. Any flag merger, sub-line restructuring, or rule simplification must be screened against the LVMH formula before adoption. The flag-to-LVMH-score mapping is not codified. | Methodologically neutral changes may be economically non-neutral for LVMH reporting. Adds an undocumented review gate to every taxonomy change. |
| 27_jp_kr | **Japan/Korea rule alignment depends on Enoco** [Updated: 2026-05] — Enoco originally drove the Japan/Korea methodology differentiation. Re-aligning these rules to the global standard (or consolidating them into a general detection rule) requires Enoco's input. Until that conversation happens, no rule consolidation in this area can proceed. | Blocks the consolidation of country-pool rules into general structural-override logic. |

---

## 4. Easily Automatable Opportunities

### Quick wins (rule-based, no AI needed)

| # | Opportunity | How |
|---|---|---|
| A | **Auto-create all presumed issues for the month** | Bulk "crea uscita presunta" based on known periodicity — already semi-implemented, just needs to run without manual clicks. |
| B | **Pre-fill cover metadata** | C1 is *always* page C1, facciata = right, positioning = "Prima di copertina". Pre-populate these three fields automatically when an operator opens a new issue. |
| C | **Auto-assign facciata from page number** | Even pages = left, odd pages = right, double = when two consecutive pages are selected. Simple parity rule (with an inversion flag for Arabic publications). |
| D | **Sequential page-number suggestion** | After the operator enters page N, pre-fill N+1 (or N+2 for doubles) on the next page. Operator confirms or overrides. |
| E | **Auto-duplicate for Marchio Commercializzato** | When an operator marks a Sold Brand, auto-generate the mirror record (swap brand, copy all fields, set commercializzato reference). Currently 100% manual. |
| F | **Default season pre-fill based on issue cover date** | Issue cover date is known. Auto-compute P/E or A/I based on Feb–Jul / Aug–Jan rule. Operator overrides only for future-season exceptions. |
| G | **Sommario value cap enforcement** | Auto-cap all Sommario records to max 1/10 total. Warn or adjust if aggregate exceeds 1/10. |
| H | **Brand filter audit report** | Generate a report of all brands with their current sub-line filter configurations. Expose brands with no filters or possibly incorrect filters. Pure database query. |
| I_adv | **Auto-stamp ADV closure** [Updated: 2026-04] | Trigger "Terminato" automatically when all pages in the ADV queue are processed, or prompt the operator with a confirmation dialog. Eliminates risk of missing the manual click. |
| J_adv | **Simplify insert creation** [Updated: 2026-04] | Replace the dummy-page creation workaround with a dedicated "Create Insert" action that does not require temporary records. Direct register → associate flow. |
| K_adv | **Integrate campaign reference file into ADV data entry UI** [Updated: 2026-04] | When the ADV operator selects a brand + magazine, display Silvana's campaign-to-category mapping inline or as a suggestion. Eliminates reliance on operator memory; enforces consistent sub-line assignment. Francesca sees this as feasible and high-impact. |

### Medium-term (OCR + text extraction)

| # | Opportunity | How |
|---|---|---|
| I | **Automatic page-number association based on actually numbered pages** | Use OCR on scanned images to detect which pages carry a printed number, then auto-assign page numbers to all pages in sequence — including inferring the correct number for unnumbered pages (inserts, covers, etc.) based on their position relative to the last detected number. Flag anomalies (missing numbers, duplicates, inserts). Operator validates or overrides. |
| J | **Brand pre-suggestion via OCR** | Extract text from editorial pages, match against the brand/sub-brand database, and pre-populate the brand field. Operator validates or corrects. |
| K | **Celebrity name extraction** | OCR + NER (named entity recognition) on captions and text to suggest celebrity names. Cross-reference against existing database; flag new names for operator confirmation. Reduces ~15/day blind creation rate. |
| L | **Section/rubrica recognition** | Match recurring section headers (e.g., "Cover Look", "Editor's Letter", "Shopping") against a per-publication rubrica dictionary to auto-suggest the service/section field. |
| M | **Campaign matching for ads** | Cross-reference ad images against a campaign database (e.g., Modelcom) using image similarity or OCR on brand/product names to suggest the campaign and product category. |
| N | **Credit block parsing** | OCR the credit block at end of fashion stories. Extract brand names, match against database, pre-populate Credit Fashion records. |
| O | **Retailer/Sold-Brand detection** | OCR captions for patterns like "disponibile da/available at [retailer]". Auto-flag for Marchio Commercializzato treatment and suggest retailer name. |
| P_ocr | **OCR: extend brand alias detection to non-Western scripts** [Updated: 2026-05] | Add Cyrillic, Arabic, CJK (Chinese/Japanese/Korean) brand name variants to the detection dictionary. Immediate improvement for APAC and MENA titles. **First priority identified by Francesca.** |
| Q_ocr | **Caption detection (structural prerequisite for AI insertion)** [Updated: 2026-04] | Reliably distinguish caption/credit text blocks from body text and image regions. Must be solved before AI can correctly assign brand records to the page where the product is visually shown (vs. the caption page). **Francesca flags this as the primary AI blocker — must be validated at test level before any AI development begins.** |
| R_ocr | **LLM-assisted reading-order reconstruction (post-Google-Vision)** [Updated: 2026-05] | Apply an LLM to the Google Vision JSON output to reconstruct correct article flow on multi-column layouts (newspapers, magazines with complex page architecture). Resolves the dominant Stage 2 failure mode where multi-word brands like "Van Cleef" are split across columns. Alberto identifies this as the highest-leverage near-term improvement. |
| S_ocr | **Open-source OCR benchmark + cost reduction** [Updated: 2026-05] | Benchmark open-source OCR models against Google Vision on representative DMR image set. Driver: ~4M images/year cost. Constraint: any replacement must emit per-word/per-character bounding boxes (required by Stage 2 alias matcher and the yellow-highlight operator UI). Suril has built a switchable framework that allows model swap via config. |
| T_llm | **OCR Stage 2 rewrite — LLM-direction renewal (Margot/Pau)** [Updated: 2026-05] | Replace the Stage 2 keyword/alias matcher with an LLM that recognizes brands and products by context and category cues, not just by verbatim string match. Distinct from R_ocr (which enhances Stage 1's output). Prerequisite: clean and consistent product/keyword catalogue (Francesca's qualification — input quality drives any LLM downstream). Pilot scope: dailies first, magazines second after caption detection is solved. |
| U_pilot | **Renewal segmentation — dailies as the pilot stream** [Updated: 2026-05] | Treat dailies and magazines as distinct renewal streams. Dailies have simpler, more uniform layouts and a narrower methodology surface area — natural pilot for any LLM-direction work. Reaffirmed as the strategic entry point across Sessions 1, 4, 7. |

### Longer-term (AI-assisted)

| # | Opportunity | How |
|---|---|---|
| P | **Product-category suggestion** | Image recognition to suggest whether the focus is bags, RTW, shoes, jewelry, beauty, etc. — but always with human validation, since campaign intent often differs from visual content. |
| Q | **Space/value estimation** | Given the page layout and the number of brands, suggest proportional space allocation. Requires layout analysis. |
| R | **Multi-cover detection** | Scan summary/editorial pages for keywords ("also on our cover", "collector's edition", "X covers") to alert the operator before they even start the issue. |
| S | **Tipo di comunicazione suggestion** | Based on page layout analysis (worn vs standalone vs text-only), suggest communication type. Especially valuable for Indossato/Indossato Marchio/Make-up Artist distinction. |
| T | **Contextualization assistant** | Given pages flagged as contextualized, auto-calculate pooled page count, distribute value proportionally, identify text-only brands for Mention treatment, compute adjusted pool. Present for operator validation. |
| U | **Corporate change monitoring** | Monitor news feeds for brand ownership/licensing changes and alert account managers proactively. |
| V_mq | **Mail Quotidiana: full automation for daily newspapers** [Updated: 2026-04] | Newspapers have simpler methodology (fewer edge cases, values mostly mentions or 1/20th page). With an improved OCR pipeline + basic brand detection, newspaper brand placement could be automated end-to-end with minimal human review. Francesca assesses this as achievable once the OCR pipeline is improved. Prerequisite: OCR multilingual upgrade (P_ocr). |
| W_mq | **Mail Quotidiana: magazine-level brand detection** [Updated: 2026-04] | Once caption detection works reliably, AI can place brand records on the correct page (product-visible page, not caption page) for magazine issues. Prerequisite: caption detection solved (see Q_ocr). |
| X_adv | **ADV campaign category pre-assignment via vision AI** [Updated: 2026-04] | AI reviews ad creative and proposes brand + sub-line (especially category: borse, abbigliamento, gioielli, etc.) based on visual analysis. Human confirms or overrides. Addresses the inconsistency created by missing campaign reference file enforcement. |

---

## 5. Strategic Takeaways from the Discussion

### From Session 1 (issue-level workflow)
- **The realistic goal is acceleration, not replacement.** Mariana and Antonella agree that full automation is unrealistic given the depth and exception-density of print data entry. The immediate objective is to reduce typing and selection time so operators shift from *data entry* to *data validation*.
- **Start with dailies (quotidiani).** They are structurally simpler — no complex covers, no multi-section layouts — making them the ideal pilot for any automation.
- **Pre-compilation is the first lever.** Before any AI, simple field pre-population (brands, celebrities, section names) based on OCR text extraction would already save significant time.
- **Quality control remains human.** The near-zero error tolerance on print (vs. web/social) means any automated output must be reviewed. The QE (Quality Engineering) team will continue to exist regardless.
- **Savings will take years.** Both participants are skeptical that headcount reductions will materialize soon — the parallel human-review phase will itself require staffing.

### From Session 2 (record-level data entry)
- **The record-level workflow is where the real complexity lives.** The cognitive load concentrates in the data entry form: brand+sub-line selection, space value estimation, Tipo di comunicazione matrix, and contextualization arithmetic. These are the highest-impact areas for automation.
- **Marchio Commercializzato is a hidden time multiplier.** Every product page mentioning a retailer doubles the work. The duplication is entirely manual and a prime candidate for automation.
- **Brand filter governance is a systemic risk.** No documented map of filter configurations, no audit trail for changes, no formal handoff between account managers and DMR. Errors surface only when clients notice incorrect data.
- **The celebrity database is growing uncontrolled.** ~15 new entries/day with no approval workflow — downstream quality implications for Discover and client reporting.
- **Several "optional" fields are operationally mandatory.** System was designed when Italy and international markets had different rules. The mismatch between system constraints and operational requirements creates a category of errors the system cannot prevent.
- **Contextualization is the most complex calculation in the workflow.** Pooling, proportional weighting, text-brand handling, pool subtraction. Strong candidate for tool-assisted calculation.
- **Untraceable deletions are a quality blind spot.** Quality control cannot distinguish "data never entered" from "data entered then deleted."

### From Session 4 (ADV insertion + Mail Quotidiana) [Updated: 2026-04]
- **ADV and EDI are parallel but distinct.** Same platform, same general framework, but different mandatory fields, different sub-line taxonomy (gender variants in ADV), different delivery cadence (ADV = same-day for ADV veloci; EDI = deadline-based). Any automation design must preserve these structural differences.
- **Caption detection is Francesca's declared primary AI blocker.** She will not proceed with AI-assisted EDI or mail quotidiana development until caption detection is demonstrably solved — not at development level but at **test level**. This must be the first AI capability to validate before any broader investment.
- **OCR multilingual upgrade is the foundation layer.** [Updated: 2026-05] Before automating either mail quotidiana or full EDI insertion, the OCR brand detection must cover non-Western scripts. Priority order: Cyrillic, Arabic, CJK. A working multilingual brand detector for mail quotidiana would also serve as the proof-of-concept for EDI automation.
- **Mail Quotidiana for daily newspapers is the easiest first automation target.** Simple data model (brand name only), minimal methodology, very few edge cases. Francesca sees it as the natural first AI step after the OCR pipeline is improved.
- **Gender separation from sub-lines is a long-standing structural debt.** Francesca has wanted for years to move gender out of the sub-line and into a standalone flag/filter. This would simplify both automation and client reporting. No timeline or ownership currently assigned.
- **Rule-based quick wins are uncontroversial and should not wait for AI.** Season pre-fill from issue date, campaign category enforcement via integrated reference file, ADV closure auto-stamp, and simplified insert creation are all agreed improvements that can proceed independently of AI roadmap.
- **CoAdv and campaign category are the two most judgment-sensitive ADV classifications.** Both involve grey areas and client disputes. They should be excluded from initial automation scope and kept as human judgment calls.

### From Session 7 (OCR renewal direction + Japan/Korea + LVMH) [Updated: 2026-05]
- **Two OCR-renewal directions need reconciliation.** The incremental Session-6 improvements (LLM-assisted reading-order on Google Vision JSON, multilingual aliases, open-source Stage 1 benchmark) and Margot/Pau's deeper LLM-direction rewrite of Stage 2 are not yet a single roadmap. Investigating the difference between "advanced OCR" (incremental) and **LLM-based** (rewrite) approaches is Mariana's open action before any commitment. See §6.6.
- **Input quality is a precondition for any LLM downstream.** Francesca: an LLM that classifies products only works if products are entered with clean, consistent spelling. The product/keyword catalogue is itself an investment area, regardless of the renewal path chosen.
- **LVMH custom score is the operative constraint on rule simplification.** [Updated: 2026-05] LVMH receives a client-specific score computed via custom formulas. Some methodology flags feed the formula, others do not. Any taxonomy simplification (flag mergers, sub-line restructuring, gender-flag separation, etc.) must be screened against the LVMH formula before adoption — a methodologically neutral change is not necessarily economically neutral. The flag-to-LVMH-score mapping is not currently codified and depends on tacit knowledge.
- **Country-specific rule pools (Japan/Korea) are operationally defensible but structurally fragile.** The structural-override logic from Session 5 works for the named pool but does not extend to similar-behaving publications outside it. Re-checking the differentiation with Enoco — who originally drove it — is the right next step. Independently, the underlying logic (Sponsored-label-with-editorial-structure → editorial) may deserve to become a general detection rule rather than a country-pool rule.
- **Dailies remain the natural first pilot for any AI work.** Reaffirmed across Sessions 1, 4, and 7: simpler methodology, more uniform layout, fewer edge cases. Any LLM-direction renewal should start there and graduate to magazines only after caption detection is solved.

---

## 6. OCR Pipeline Architecture [Updated: 2026-05]

> **Transcription note:** Earlier session auto-transcripts (notably Session 4) rendered "OCR" as **"SIAR"** — this is a recurring mistranscription of the English pronunciation "oh-see-arr", not an actual system name. There is no system called SIAR. All references in this document use **"OCR pipeline"** as the canonical name.

### 6.1 Where the pipeline runs
- **Application name:** **Print Image Management** — internal application used by the digitalization team to convert PDFs / physical magazines into image assets at the correct resolutions.
- **Storage:** images are written to an **S3 bucket** (date-tree structure: `year/month/...`) and indexed in a database table accessible via Web Digital and Databricks.
- **Two image formats are produced:** a high-resolution version (final asset used by client platforms) and small thumbnails (used in galleries and previews).

### 6.2 Pipeline stages

The pipeline has **two distinct stages**, run sequentially per image:

**Stage 1 — Text extraction (third-party OCR):**
- Each new image enters the queue table **`OCR_Image_Queue`**.
- The image is sent to the **Google Vision API**.
- Google Vision returns a JSON response containing the full text and a hierarchical structure: `pages → blocks → paragraphs → words → symbols`, each with bounding-box coordinates down to the single-character level.
- The JSON is persisted to S3 (separate bucket from the images themselves).
- **Cost note:** Launchmetrics processes ~4 million images/year through Google Vision. This is a meaningful commercial cost line and a key motivator for evaluating open-source alternatives.

**Stage 2 — Brand identification (DMR custom code):**
- A custom matching engine (written by Alberto Tornielli + Massimiliano) iterates **character by character** through Google Vision's JSON output.
- It matches text fragments against the **brand alias list** maintained internally.
- For each match, it records: `brand_id`, `image_id`, the **exact word that matched** the alias, and the **bounding-box coordinates** of the match within the image.
- Output tables (approximate names — to be confirmed):
  - `Image_Brand` — list of brands identified per image (one row per brand-image pair).
  - `Image_Brand_Word` — coordinates of each matched word, used to draw the **yellow highlight rectangle** in the operator UI.

### 6.3 Key technical limitations

| Limitation | Mechanism | Impact |
|---|---|---|
| **Google Vision does not understand reading order** | It splits text into blocks based on **whitespace only** (no LLM, no layout/semantic understanding). | On magazines (single-flow articles) this works well. On newspapers and multi-column layouts, the same article is fragmented into separate blocks in arbitrary order. |
| **Multi-column brand splits** | When a brand name spans two columns (e.g., "Van" at the end of column 1, "Cleef" at the start of column 2), Google Vision treats them as different blocks. | Stage 2 alias matching fails — the brand is missed entirely. **Single-word brands** (Gucci, Prada) are unaffected; **multi-word brands** (Van Cleef & Arpels, Patek Philippe) are at risk. |
| **Character-by-character iteration in Stage 2** | Custom code loops through every symbol returned by Google Vision, including spaces, underscores, and punctuation. | Heuristic logic is in place to detect column adjacency and merge fragments, but it does not always succeed. |
| **Keyword/alias-based matching is not semantic** | Stage 2 matches on string patterns from the alias list. | False positives (recall-prioritized design); no language-agnostic detection; non-Western scripts (Cyrillic, Arabic, CJK) are largely uncovered in the alias list. |

### 6.4 LLM and open-source OCR evaluation (in progress)

- **LLM-based reading-order reconstruction** — Alberto's view: an LLM applied **after** Google Vision (operating on the JSON output) could reconstruct the correct article flow on newspapers and resolve the multi-column brand-split problem. This is the most promising near-term improvement.
- **Open-source OCR replacement** — under evaluation by Suril Vara. Driver is cost (the ~4M images/year Google Vision spend), not accuracy — Alberto considers Google Vision "very good" on character recognition. Suril has built a **switchable framework** (configuration-driven) that allows different OCR models to be plugged in and benchmarked against the same image set. Initial open-source tests showed lower accuracy on brand/title/product extraction; further benchmarking pending.
- **Key constraint for any replacement:** any new OCR must produce a comparable output structure — at minimum, the list of detected text fragments with bounding-box coordinates. Without coordinates, Stage 2 matching and the operator-side yellow-highlight UI both break.

### 6.5 Coexistence with the future LLM/AI roadmap

Per Mariana (citing Margot): the current OCR pipeline **will remain in operation** even after broader LLM/AI capabilities are added downstream. The reason is that **Discover** uses the OCR text content to power **keyword search inside print articles** — this is a live client capability that depends on the existing OCR output and cannot be regressed. Any new AI layer must be additive, not a replacement.

### 6.6 OCR renewal — LLM-direction hypothesis (Margot/Pau) [Updated: 2026-05]

A second renewal direction is in scoping, distinct from the incremental improvements in §6.4:

- **Hypothesis (Margot + Pau):** rewrite Stage 2 around an **LLM** that recognizes brands and products by **context and category cues**, not just by string match against the alias list. Differentiates from §6.4 R_ocr (LLM-assisted reading-order on Google Vision JSON), which is an enhancement to Stage 1's output, not a Stage 2 rewrite.
- **Why:** the current Stage 2 matcher only finds brands when their alias appears verbatim in the extracted text. An LLM could disambiguate similar brand names, recognize products without an explicit brand mention, and reduce dependency on alias-list completeness.
- **Francesca's qualification:** input keyword/product spelling quality remains a foundational issue. An LLM downstream depends on a clean, consistent product catalogue upstream. Cleaning the catalogue is therefore not optional even in an LLM-rewrite scenario.
- **Segmentation:** the renewal should treat **dailies and magazines as distinct streams**. Dailies have simpler, more uniform layouts and should be the pilot for any LLM-direction work (consistent with Session 1 takeaway: "start with dailies").
- **First milestones (Mariana's commitment):** (a) define the full ADV-space taxonomy as a renewal-scope input; (b) advance the technological assessment with Alberto on what is developable in the alias/product catalogue.
- **Open scoping question:** the §6.4 incremental improvements (LLM reading-order, open-source benchmark, multilingual aliases) and the §6.6 LLM-direction rewrite are not yet reconciled into a single roadmap. Tracked as OQ-26.
