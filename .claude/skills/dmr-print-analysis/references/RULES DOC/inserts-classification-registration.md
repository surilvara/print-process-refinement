# Inserts — Classification & Registration Rules

**Sources:**
- `regole_inserti_x_registrazione.pdf` — Italian registration manual (Omniapress, 2015)
- `Inserts_classification.docx` — English classification manual (international standard)

---

## Overview

Inserts are non-standard pages physically attached to or included with a magazine. They are classified into three main families:

| Family | Code prefix | Description |
|---|---|---|
| **Gatefolds / Battenti** | GATEFOLD / BATTENTE | Pages attached to (beating against) the cover |
| **Bonded inserts** | BC (Brossurato/Bonded Cover) | Thick pages directly bound into the magazine |
| **Loose inserts** | LC (Loose Cover) | Free-standing inserts found in or with the magazine's wrapping |

---

## 1. Gatefolds / Battenti

Thick pages connected to the cover that fold out. Two sub-types:

### 1A — Gatefold on C1 (OFC / Outside Front Cover)

Typical: 2 pages; sometimes 3 (1 cut in 2 half-pages + 1 full page) or more.

**Page numbering:** C1b1/b2 (2 pages), C1b1-b3 (3 pages)

**Issue Manager / Registration:**
- Type: GATEFOLD (or BATTENTE in Italian system)
- Format: 1X
- Total pages: 2 or 3
- Brand name
- Notes: mark any non-standard elements (WINDOW, TRANSPARENT PAPER, etc.)

**Scanning:** Scan all pages following the order they appear when the folder is open. For "Folder Window" (Fig. 3): merge the two cover halves into one single image; keep the two advertising halves separate → 3 total pages.

**Values:**
- C1b1/b2 (double page) → VALUE: 2 FP
- C1b1 (single RH) + C1b2 (single LH) → VALUE: 1 FP each
- C1b1 (LH half-page) + C1b2 (RH full page) + C1b3 (RH half-page) → VALUE: 1 HP + 1 FP + 1 HP

### 1B — Gatefold on C2 (IFC / Inside Front Cover)

Typical: 4 pages, but sometimes 3 because the 4th is editorial (thin paper).

**Page numbering:** C2b1/b3 (example for 3 pages); C2b1, C2b2/b3

**Issue Manager / Registration:**
- Type: GATEFOLD
- Format: 1X
- Total pages: as applicable
- Brand name

**Values:**
- C2b1 (single RH) → VALUE: 1 FP
- C2b2/b3 (double page) → VALUE: 2 FP

---

## 2. Bonded Inserts (BC — Brossurato/Bound)

Thick pages directly bonded (bound) into the magazine. Classified by type:

### 2A — BC Recto/Verso (Italian: Bianca e Volta)

A thick single page where **both faces show advertising of the same brand**.

**Page numbering:** previous page + i + progressive (e.g., 120i1/i2)

**Issue Manager / Registration:**
- Type: BC – RECTO/VERSO (Italian: BC – BIANCA & VOLTA)
- Format: 1X (or smaller if smaller than standard page)
- Total pages: 2
- Brand name
- Notes/Campione Prodotto: mark if there is a scent strip or product sample

**Scanning:** Scan front and back normally; do not rename the file.

**Values:**
- 120i1 (RH single page) → 1 FP
- 120i2 (LH single page) → 1 FP

### 2B — BC Page (Italian: Brossurato Pagina)

A thick single page where **one face is editorial and the other is advertising**, or both faces are advertising from **two different brands**.

**Page numbering:** previous page + i + progressive (e.g., 30i1/i2)

**Issue Manager / Registration:**
- Type: BC – PAGE (Italian: BC – PAGINA)
- Format: 1X (or smaller)
- Total pages: 2
- Brand name (ADV brand only)
- Notes: mention if one page is editorial

**Scanning:** Scan front and back normally; do not rename the file.

**Values:**
- 30i1 (RH) → 1 FP; 30i2 (LH) → 1 FP
- Note: sometimes these pages follow magazine numbering — in that case, use their printed number.

### 2C — BC Booklet (Italian: Booklet Catalogo)

Thick multiple pages, advertising all for **one single brand/company**. Three sub-variants:

**Sub-variant A — Same size as magazine, cartonated:**

**Page numbering:** previous page + i + progressive (e.g., 50i1/i4)

**Issue Manager / Registration:**
- Type: BC – BOOKLET (Italian: BC – BOOKLET/CATALOGO)
- Format: 1X
- Total pages: 4 (or more)
- Brand name

**Values:** 50i1 (RH) → 1 FP; 50i2/i3 (double) → 2 FP; 50i4 (LH) → 1 FP
- Note: sometimes pages follow magazine numbering — use printed numbers.

**Sub-variant B — Smaller format, clipped to magazine:**

**Page numbering:** 50i1/i12 (first to last)

**Issue Manager / Registration:**
- Type: BC – BOOKLET/CATALOGO
- Format: 1/2 (or actual size relative to magazine page)
- Total pages: as applicable (e.g., 12)
- Brand name

**Scanning:** Scan only the first page.

**Values:** 50i1/i12 → 1 FP (the entire booklet counts as 1 FP regardless of page count)

**Sub-variant C — Small booklet glued to the advertising page:**

**Issue Manager:** Do NOT create an insert record.
**Scanning:** Scan the ADV page with the glued booklet as it appears.
**Data entry:** Register the ADV page normally; note the booklet presence in the **Campione Prodotto / Product Sample** field.

### 2D — BC Folder (Italian: Folder)

Thick, **folded** multiple pages about the same brand. May contain editorial pages between folds.

**Page numbering:** previous page + i + progressive (e.g., 50i1/i4)

**Issue Manager / Registration:**
- Type: BC – FOLDER
- Format: 1X (or actual size; note different formats in description)
- Total pages: as applicable
- Brand name
- Notes: mention any editorial pages or non-standard formats

**Scanning:** Scan all pages following the order they appear when the folder is open. Rename consecutively.

**Values (4-page example):**
- 50i1/i2 (double) → 2 FP; 50i3 (LH) → 1 FP; 50i4 (LH) → 1 FP
- Or: 50i1/i2 (double) → 2 FP; 50i3/i4 (double) → 2 FP

**Folders with editorial pages (clipped magazines — common case):**
Folder pages may appear split across the magazine (e.g., 10i1/i2 at p.10, then 50i1/i2 at p.50 — all part of the same insert).

**Issue Manager / Registration:**
- Page number: 10i1/i2–50i1/i2
- Type: BC – FOLDER; Format: 1X; Total pages: 4; Brand name
- Description: note the different format (1/2) for the pages at p.50

**Data entry:** Create the BC – FOLDER insert once. For the smaller pages (50i1/i2), select the previously created insert and change the format to 1/2 in the **page data** (not in the insert creation).

**Scanning:** Scan pages in the positions where they appear; do not rename.

### 2E — BC Group (Italian: Gruppo)

Thick multiple pages featuring **different brands**.

**Page numbering:** previous page + i + progressive (e.g., 60i1/i6)

**Issue Manager / Registration:**
- Type: BC – GROUP (Italian: BC – GRUPPO)
- Format: 1X
- Total pages: as applicable
- Brand names: list all brands in the group

**Values:** Each page to its respective brand (1 FP per page, or 2 FP per double).

**Important note:** Mall catalogues (e.g., Harrods) are NOT entered as BC – GROUP despite containing multiple brands. They are entered as **BC – BOOKLET** for the mall's own brand.

### 2F — BC Postcard (Italian: Cartolina)

A bonded/clipped two-faced postcard.

**Page numbering:** previous page + i + progressive (e.g., 10i1/i2 or 60i1/i2)

**Issue Manager / Registration:**
- Type: BC – POSTCARD (Italian: BC – CARTOLINA/SAGOMATO/CARD)
- Format: 1/4 (or 1/2 as applicable)
- Total pages: 2
- Brand name

**Scanning:** Scan front and back, adjust size; do not rename.

**Values:** 60i1 (RH) → 1 FP; 60i2 (LH) → 1 FP

---

## 3. Loose Inserts (LC — Loose Cover)

Free-standing inserts found loose in or with the magazine's wrapping. They are **not bound** to the magazine in any way.

**Key valuation rule: regardless of the number of pages, a loose insert always counts as 1 single page.**

**Page numbering:** I1 (first loose insert), I2, I3, etc. if multiple loose inserts in the same issue.

**Types:**
- LC – PAGE (single-faced flyer)
- LC – BOOKLET (brand or mall catalogue)
- LC – FOLDER (folded multi-page flyer)
- LC – POSTCARD (not magazine subscription card)

**Issue Manager / Registration:**
- Page number: I1 (or I2, I3 for multiple)
- Type: appropriate LC type
- Format: as applicable (e.g., 1/2 for smaller booklet)
- Total pages: actual count
- Brand name

**Scanning:** Scan only the first page; rename file as I1 (or I2, I3 progressively).

**Values:** I1 → **1 FP** (the entire loose insert counts as 1 full page, regardless of actual page count).

---

## Summary Table

| Type | Code | Format | Scanning | Value rule |
|---|---|---|---|---|
| Gatefold C1 | GATEFOLD/BATTENTE | 1X | All pages, open order | 1 FP per page |
| Gatefold C2 | GATEFOLD/BATTENTE | 1X | All pages, open order | 1 FP per page |
| BC Recto/Verso (Bianca e Volta) | BC – RECTO/VERSO | 1X | Front + back | 1 FP per face |
| BC Page (Brossurato Pagina) | BC – PAGE | 1X | Front + back | 1 FP per face |
| BC Booklet full-size | BC – BOOKLET | 1X | All pages | 1 FP per page |
| BC Booklet small-format | BC – BOOKLET | 1/2 (or actual) | First page only | 1 FP total |
| BC Booklet glued to page | — | — | ADV page | Note in Campione Prodotto |
| BC Folder | BC – FOLDER | 1X | All pages, open order | 1 FP per page |
| BC Group | BC – GROUP | 1X | All pages | 1 FP per page, per brand |
| BC Postcard | BC – POSTCARD | 1/4 or 1/2 | Front + back | 1 FP per face |
| Loose Insert | LC – (type) | as applicable | First page only | 1 FP total (always) |

---

## Campione Prodotto / Product Sample Field

Mark in this field when any of the following is physically attached to the page:
- Scent strip (banda profumata)
- Product sample (campione)
- Postcard (cartolina)
- Card (tessera/card)
- Glued booklet catalogue

---

## Page Numbering Convention for Inserts

| Situation | Numbering pattern | Example |
|---|---|---|
| Bonded insert (BC) | [prev page] + i + [progressive] | 50i1, 50i2, 50i3 |
| Bonded insert spanning two positions | [prev page 1]i1/i2–[prev page 2]i1/i2 | 10i1/i2–50i1/i2 |
| Gatefold on C1 | C1b + [progressive] | C1b1, C1b2 |
| Gatefold on C2 | C2b + [progressive] | C2b1, C2b2, C2b3 |
| Loose insert | I + [progressive] | I1, I2, I3 |
| Pages with own numbering | Use printed number | as printed |
