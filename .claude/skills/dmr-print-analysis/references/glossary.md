# DMR Glossary — Unified Reference

This glossary consolidates all key terms used across DMR print data entry: system/UI terms, classification terminology, insert types, and methodology concepts. Use it as a quick-lookup reference across all topics.

---

## System, Navigation & UI

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

---

## Page-Level Fields

| Term | Type | Description |
|---|---|---|
| **Numero pagina** | Field | The page number. Typed manually; must match the printed number on the page. |
| **Facciata** | Field (dropdown) | Page orientation: Sinistra (left), Destra (right), or Doppia (double spread). |
| **Posizionamento** | Field (dropdown) | Page type: Singola (single), Doppia (double), or special values — Prima di copertina, Sommario, Editoriale, Staff, Indirizzi. |
| **Servizio / Rubrica** | Field | The editorial section or service name (e.g., "Cover Look", "Moda", "Beauty"). Mandatory for regular pages only. |
| **Titolo** | Field | Article or feature title. Mandatory for regular pages only. |
| **Tipo di testo** | Field | Text classification. Mandatory for regular pages only. |
| **Valore / Spazio** | Field | The proportional space a brand occupies on the page (e.g., 1/20, 1/15, 1/8, 1/6). |

---

## Page Naming & Numbering Conventions

| Term | Description |
|---|---|
| **C1, C2, C1a, C1b…** | Cover page identifiers. C1 = front cover, C2 = inside front cover. Multi-cover issues use alphabetical suffixes (C1a, C1b, C1c…). |
| **C1b1, C1b2…** | Gatefold pages attached to the front cover. |
| **C2b1, C2b3…** | Gatefold pages attached to the inside front cover. |
| **R1** | First editorial page after the cover section. |
| **I + progressive** | Insert numbering for uncounted pages: last numbered page + "I" + sequential number (e.g., 9.I1, 9.I2, 9.I3). |
| **Alphabetical suffixes (A, B, C…)** | Used for mid-magazine supplements with their own numbering or printing errors that restart pagination. |
| **"bis"** | Used to handle duplicate page numbers caused by printing errors. |

---

## Priority & Workflow

| Term | Description |
|---|---|
| **Priorità 1 / 2 / 3 (P1, P2, P3)** | Priority tiers assigned to each publication. P1 = highest urgency, shortest deadline. |
| **Collage** | A composite image created by the scanning team showing all covers of a multi-cover issue side by side. Becomes the C1 thumbnail. |
| **Registration (Check-in)** | The process of logging a magazine's arrival: setting the arrival date, source, and verifying physical condition before scanning. |

---

## Insert Types (Physical Magazine)

| Term | Description |
|---|---|
| **Gatefold (Battente)** | Thick fold-out pages connected to a cover or inner page. Can be on C1 (OFC) or C2 (IFC). Usually 2–4 pages. Format 1X. |
| **Reverse Gatefold** | A gatefold that folds the opposite way — scanned before the front cover in page order. |
| **Bonded Insert (BC)** | An advertising page physically glued into the magazine. Typically recto/verso (2 pages). May contain product samples or scent strips. |
| **Loose Insert** | A separate piece (card, booklet, sample) placed inside but not attached to the magazine. |
| **Sample (PDT Sample)** | A physical product sample (e.g., perfume, cream) attached to a bonded insert. Recorded in the PDT Sample area of the data entry form. |
| **Window / Transparent Paper** | Non-standard gatefold elements noted in the insert description field. |

---

## Classification & Methodology Terms

| Term | Description |
|---|---|
| **Still Life** | A product photograph without a model — objects displayed on their own. |
| **Credits on Model** | A photograph where products are worn/used by a model and identified via caption credits. |
| **Total Look (TL)** | When a model is dressed head to toe in items from a single brand. Each item is recorded under its product line with the TL flag. Also applies when only one brand is mentioned or captioned. |
| **Indossato** | "Worn" — flag indicating brands are physically worn by a person in the image. |
| **Foto prodotto** | "Product photo" — flag indicating the image shows a standalone product shot. |
| **Mention (1 Mention)** | Minimum classification: a brand/product is named but not visually prominent or specifically described. Also used when a product is described in caption but not visible in the image. |
| **Full Page** | Space allocation: the brand occupies one entire page. Split proportionally when multiple brands share a page. |
| **Half Page (HP)** | Space allocation: the brand occupies half a page. |
| **Contextualization** | Recording a brand that appears incidentally in a page where it is not the editorial focus (e.g., a recognizable bag in a fashion story about another brand). |
| **Recognized Products** | (Fashion only) Products that are identifiable by their design even without caption credits — e.g., iconic bags, shoes, patterns. |
| **Location** | (Fashion only) When a recognizable location (hotel, restaurant, landmark) appears in an editorial and is relevant to monitoring. |
| **Monography** | An article entirely dedicated to one brand or subject. Three sub-types: Product, Corporate, Testimonial. |
| **Product Monography** | A monographic article focused on a brand's products. |
| **Corporate Monography** | A monographic article about the brand/company itself (history, strategy, etc.). |
| **Testimonial Monography** | A monographic article centered on a celebrity/testimonial associated with a brand. |
| **Advertorial (Publiredazionale)** | Paid content that looks editorial but is advertising. Classified differently from both pure editorial and pure ads. See `advertorials.md` for identification rules. |
| **Tie-up** | A specific type of advertorial, often multi-page, with editorial-style content paid for by the brand. |
| **Costume Jewellery** | Fashion accessories that imitate fine jewellery but are made of non-precious materials. Classified under Fashion sector. |
| **High Jewellery** | Fine jewellery pieces made of precious materials (gold, platinum, gemstones). Separate classification from standard jewellery (rule updated — see `training-rules.md` §3). |
| **Beauty Taxonomy** | The product categorization system for beauty items: make-up, skincare, fragrance, hair, etc. See `training-rules.md` §11 for the full taxonomy. |
| **Iconic Bags & Shoes** | A product association project for recognizable luxury accessories. See `training-rules.md` §12 for the identification guide. |
| **Indossato Marchio** | (Beauty only) Tipo di comunicazione used when the caption credits a brand (e.g., "Make-up: Dior") but does not specify the exact product. |
| **Make-up Artist** | (Beauty only) Tipo di comunicazione used when a make-up artist is credited by name in association with a brand. |
| **Credit Fashion** | (Fashion only) Tipo di comunicazione used when brands are listed in an aggregated credit block (usually end-of-service) and cannot be attributed to specific pages. |
| **Articolo** | Tipo di comunicazione: brand mentioned in text only, no image. |
| **Marchio Commercializzato (Sold Brand)** | When a retailer (e.g., Sephora) is cited alongside a product brand (e.g., Dior), both get duplicate records with the same space value. The retailer's record has the Marchio Commercializzato field set to the product brand. Rule introduced by France. |
| **Oggetti (Objects)** | Number of visible items of a brand on the page. Default 1. Object 0 = mention-only (brand cited but no visual space). |
| **Stagione (Season)** | Biannual assignment: P/E (Spring/Summer) for Feb–Jul issues; A/I (Autumn/Winter) for Aug–Jan. Only current and future selectable. |
| **Collezioni passate** | Special sub-line for past-season items when past seasons are not selectable in the system. Combined with the current season. |
| **Sottolinea (Sub-line)** | The combination of gender + product category (e.g., "Donna — Abbigliamento"). Filtered per brand via configurable settings. |
| **Filtri (Sub-line filters)** | Configurable restrictions on which sub-lines appear per brand. Set via Anagrafiche → Marchi by Antonella/Alberto. Prevent cross-sector errors. |
| **Duplica** | Action that copies all fields of a record into a new one. The operator changes only what differs (e.g., brand). Major time-saver for pages with many similar items. |
| **Bridal Product** | Flag for jewellery/products featured in wedding specials. |

---

## ADV-Specific Terms [Updated: 2026-04]

| Term | Type | Description |
|---|---|---|
| **ADV veloci** | Service / Report | Same-day publisher reports that list all advertising placements for the brands in a publisher's scope. Requires ADV insertion to be completed on the day the issue is published. |
| **Fine Inserimento ADV / Terminato** | Action | Manual button the ADV operator must click to stamp the ADV closure date after all advertising pages are entered. Not triggered automatically. |
| **Contapagine** | Action | Page count for an issue. Must be run by the first team (ADV or EDI) to open the issue. |
| **Campione Prodotto** | Field (ADV) | Flag for physical samples physically attached to the page: banda profumata (scented strip), sample, tessera (card), cartolina (postcard). Relevant only for publisher reports; no impact on MIV. |
| **Banda profumata** | Insert sub-type | A scented paper strip glued to or inserted in a page, typically for fragrances. Flagged under Campione Prodotto. |
| **PR flag (Publiredazionale)** | Field (ADV + EDI) | Flags an ad that looks like editorial content. Can be identified and entered by either ADV or EDI team. Always counted as ADV in client analysis. Use minimum sub-lines (typically 1). |
| **CoAdv / PTD (co-advertising)** | Field (ADV) | Marks an ad paid by two parties (brand + retailer, or two brands). The cost split is implicit from having two records on the same page; PTD is additional metadata for filtering. Grey area: contested by clients. |
| **Regalo con Acquisto** | Flag (ADV) | Gift-with-purchase: ad explicitly offering a free gift for a purchase alongside the advertised product. |
| **Posizione in pagina** | Field (ADV) | Small-format position within the page: finestrella, banner, box, piedino. Used primarily for daily newspapers; rare in magazines. Relevant for publisher reports. |
| **Biancavolta** | Insert type | A detachable page where both the front and back are advertising for the same brand. Always 2 pages; format = "1×2". |
| **Battente** | Insert type | A gatefold or folded cover extension. Pages may be unnumbered. Typically 2–6 pages; format expressed as "1×N pages". |
| **Inserto libero** | Insert type | A loose, free-standing insert not bound into the magazine. Regardless of its number of pages, always valued as 1 full page. |
| **Inserto rilegato** | Insert type | A bound insert within the magazine. Valued by the space it occupies (same scale as regular pages). |
| **Formato (inserto)** | Field | Insert size expressed as multiplier × pages (e.g., "1/3" for a small booklet, "1×2" for a 2-page gatefold, "1×4" for a 4-page poster). The "1×" prefix indicates a full-size-page insert of N pages. |
| **Abbigliamento Uomo/Donna** | Sub-line (ADV) | Combined gender sub-line used in ADV when a single creative features both men's and women's clothing. Equivalent combined variants exist for Profumo and other categories. |

---

## Mail Quotidiana Terms [Updated: 2026-04]

| Term | Description |
|---|---|
| **Mail Quotidiana** | A separate program (not connected to the main EDI/ADV system) used to send daily brand-presence previews to publisher clients for a specific list of titles. Entry is brand-name only. |
| **Uscite Pagine Marchi** | The entry mask within the Mail Quotidiana program where the operator selects country → publication → date and enters brand names per page. |
| **Gallery verticale** | The vertical page-pair gallery within Mail Quotidiana, where pages are displayed as left-right pairs. Cover appears alone on the right; all subsequent pages are paired. |
| **Link intestino** | The internal link button between page pairs in Mail Quotidiana that the operator uses to confirm or break a double-page association. |
| **Regola di placement (caption vs. prodotto)** | Critical Mail Quotidiana rule: the brand must be entered on the page where the product is **visually shown**, NOT on the page containing the caption or credits. The caption page may be on the facing page, at the end of the article, or at the end of the magazine. This rule is the primary blocker for AI-assisted automation. |
| **PDF con highlight** | PDF generated from the Mail Quotidiana system showing brand occurrences highlighted. Two versions: one scoped to mail quotidiana brands only; one scoped to all EDI insertion brands. Available via "Esporta uscita in PDF" in Gestione Uscite. |
| **Gruppo (mail quotidiana)** | A publisher group in the Mail Quotidiana system. Each group has a list of recipient email addresses and an associated list of brands. Data is extracted per group and sent to those addresses. |
| **OCR pipeline** [Updated: 2026-05] | The end-to-end brand detection system that supports Mail Quotidiana and EDI pre-annotation. Two stages: **Stage 1** = text extraction via Google Vision API (returns full text + bounding boxes per character); **Stage 2** = brand alias matching via DMR custom code (matches Stage 1 output against a brand alias list, records `brand_id`, `image_id`, matched word, and bounding-box coordinates). Limitations: brand alias dictionary is Western-script-biased; Google Vision splits text by whitespace only (no semantic understanding) so multi-word brands split across columns are missed; recall-prioritized over precision. **Note:** earlier auto-transcripts mistranscribed "OCR" as "SIAR" (English pronunciation "oh-see-arr"). There is no system called SIAR. |
| **`OCR_Image_Queue`** [Updated: 2026-05] | Database table that holds images awaiting OCR processing. Accessible from Web Digital and Databricks. Each row = one image queued for Stage 1 (Google Vision) and Stage 2 (brand identification). |
| **Print Image Management** [Updated: 2026-05] | Internal application used by the digitalization team to convert PDFs/physical magazines into image assets at correct resolutions and feed them into the OCR pipeline queue. |
| **Google Vision API** [Updated: 2026-05] | The third-party OCR service currently used in Stage 1 of the OCR pipeline. Returns hierarchical JSON: pages → blocks → paragraphs → words → symbols, with bounding boxes at every level. Strong on character recognition; weak on reading order / semantic layout. ~4M images/year processed by Launchmetrics. |
| **Image_Brand / Image_Brand_Word** [Updated: 2026-05] | Output tables of OCR pipeline Stage 2 (approximate names). `Image_Brand` = one row per detected brand per image. `Image_Brand_Word` = bounding-box coordinates of each matched word, used to render the yellow highlight rectangle in the operator UI. |
| **LVMH Score** [Updated: 2026-05] | A client-specific score computed for LVMH using **custom formulas**, distinct from the standard MIV calculation. Several methodology flags affect this score (e.g., flags applied to records contribute to or are excluded from the LVMH formula); other flags do not impact it. Any change to flag taxonomy or rule definitions must be reviewed for LVMH-score impact before being adopted. |

---

## Article / Page Types

| Term | Description |
|---|---|
| **TOC (Table of Contents / Sommario)** | The magazine's index page. Special positioning — different rules for fashion vs beauty regarding brand credits. |
| **Addresses (Indirizzi)** | Brand contact/store listing pages. Special positioning. |
| **Previews / Openings** | Introductory pages for a section. Special positioning. |
| **Pages.com** | Digital/web reference pages in print magazines. Special positioning. |
| **Double Page (Doppia)** | A spread across two facing pages. Specific rules determine when a still life on a continuous background counts as double vs. two singles. |
| **Cover Look** | A rubrica/section dedicated to recreating or analyzing the cover outfit. |
| **Editor's Letter (Editoriale)** | The editor's introductory column. Special positioning. |
| **Staff** | The magazine's staff/masthead page. Special positioning. |

---

*Last updated: auto-generated from dmr-print-knowledge.md, training-rules.md, fashion-methodology.md, beauty-methodology.md, inserts-and-registration.md, advertorials.md, session-4_adv-insertion-mail-quotidiana.md, general-rules.md, stores-ecommerce.md, inserts-classification-registration.md.*

---

## Insert Types — Extended Glossary [Updated: 2026-04]

| Term | Code | Description |
|---|---|---|
| **Gatefold / Battente** | GATEFOLD or BATTENTE | Thick pages attached to the cover that fold out. Sub-types: C1 (OFC) gatefold and C2 (IFC) gatefold. Pages numbered C1b1, C1b2… or C2b1, C2b2… |
| **BC – Recto/Verso (Bianca e Volta)** | BC – RECTO/VERSO | Thick single page where both faces show advertising for the same brand. Always 2 pages, format 1X. |
| **BC – Page (Brossurato Pagina)** | BC – PAGE | Thick single page where one face is editorial and the other is advertising, or both faces are advertising from two different brands. |
| **BC – Booklet** | BC – BOOKLET | Thick multiple pages with advertising all for one brand. Three sub-variants: (A) full-size cartonated, (B) smaller format clipped, (C) glued to the ADV page. Sub-variant C: not registered in Issue Manager; noted in Campione Prodotto. |
| **BC – Folder** | BC – FOLDER | Thick folded multiple pages about the same brand. May have editorial pages between folds. Can appear split across different positions in the magazine. |
| **BC – Group (Gruppo)** | BC – GROUP | Thick multiple pages featuring different brands. Note: mall catalogues (e.g., Harrods) are NOT Group but Booklet for the mall brand. |
| **BC – Postcard (Cartolina/Sagomato/Card)** | BC – POSTCARD | Bonded two-faced postcard. Format: 1/4 or 1/2. |
| **LC – Loose Insert** | LC – [type] | Free-standing insert, not bound to the magazine. Found loose in or with the wrapping. Regardless of page count: always valued as **1 FP total**. Numbered I1, I2, I3. Scan first page only. Sub-types: LC – PAGE, LC – BOOKLET, LC – FOLDER, LC – POSTCARD. |

---

## General Rules Glossary [Updated: 2026-04]

| Term | Description |
|---|---|
| **Le Aziende Informano** | Editorial sections produced by the magazine's editorial staff (not advertising). Brands/products valued for space occupied; divide page equally among items present. |
| **Rivista Sponsorizzata** | Sponsored magazine/supplement: a sponsor brand is present on every page. All pages → sponsor brand as full page publiredazionale. Other-sector brands → editorial for space. Same-sector brands → omitted. |
| **Supplemento "in collaborazione con"** | "In association with" supplement: normal editorial structure, simply co-published with a brand. Treat as normal supplement. The associate brand logo wherever visible → 1/20 editorial. |
| **Catalogo Pubblicitario** | Advertising catalogue booklet: no magazine reference on cover. Treated as ADV insert, not sponsored supplement. |
| **Testata con Traduzione Incorporata** | Magazine with embedded translation. Text-only translations: not counted. Translation on facing page with new images: valued as full page. Translation on same page: ignored, original text spreads across full page. |
| **Tie-up (Japanese magazines)** | Pages structured like editorial monographies but paid by a brand. Identified by brand contact info at end of service (when the magazine has a dedicated indirizzi page). Classified as publiredazionale. Three exception categories: recurring brand-rotation sections, magazines without indirizzi pages, watch magazines with contact info on every article. |
| **Associazioni di Categoria** | Trade associations (Woolmark, Verocuoio, World Gold Council, DTC, Cotton USA). Their advertorials are an exception: brands present within them are entered as editorial for space occupied. |

---

## Stores & E-Commerce Glossary [Updated: 2026-04]

| Term | Description |
|---|---|
| **Marchio Commercializzato** | Field set on the store/e-commerce retailer's record to indicate which product brand it is selling. When a caption says "Product X at Store Y", Store Y gets a record identical to Product X's record, with Marchio Commercializzato = Product X. |
| **Negozio / Sito E-Commerce** | A physical store or online retailer cited in a caption as the place where a product can be purchased. Always entered as a separate record mirroring the product brand, with Marchio Commercializzato set. |
