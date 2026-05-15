# Stores & E-Commerce Insertion Rules

**Source:** INSERIMENTO NEGOZI E SITI E-COMMERCE (official DMR manual)

---

## Core Rule

Whenever a caption mentions a store or e-commerce site where a product is sold, the **store/e-commerce brand must be entered and valued exactly like the product brand it sells**.

This applies to **all sectors** (fashion, beauty, jewellery, watches, etc.).

### Fields to mirror (identical to the product record):
- Sottolinea (same sub-line)
- Valore/Spazio (same space value)
- Tipo di comunicazione (same type)
- Oggetti (same number of objects)
- Celebrity (same, if applicable)

### Additional mandatory field:
- **Marchio Commercializzato** — set to the product brand being sold at the store.

---

## Entry Structure

For each product brand sold at a store/e-commerce, create **two records**:

| Record | Brand | Sub-line | Space | Tipo | Marchio Commercializzato |
|---|---|---|---|---|---|
| 1 | Product brand (e.g. Fendi) | Borse | 1/4 | Foto prodotto | — |
| 2 | Store brand (e.g. Saks Fifth Avenue) | Borse | 1/4 | Foto prodotto | FENDI |

---

## Examples

### Example 1 — Single brand at a store
**Caption:** *"…leather mini bag by Fendi at Saks Fifth Avenue"*

- Fendi — Borse — 1 oggetto — foto prodotto — 1/4
- **Saks Fifth Avenue — Borse — 1 oggetto — foto prodotto — 1/4 — FENDI**

### Example 2 — Single brand at e-commerce
**Caption:** *"…red blazer and trousers MSGM at Mytheresa.com"*

- MSGM — Abb. Donna — 2 oggetti — foto prodotto — 1/6
- **Mytheresa.com — Abb. Donna — 2 oggetti — foto prodotto — 1/6 — MSGM**

### Example 3 — Multiple brands at the same store
**Caption:** *"…Tom Ford velvet jacket and Kiton pants, both at Neiman Marcus"*

- Tom Ford — Abb. Uomo — 1 oggetto — indossato — 1/6
- Kiton — Abb. Uomo — 1 oggetto — indossato — 1/6
- **Neiman Marcus — Abb. Uomo — 1 oggetto — indossato — 1/6 — TOM FORD**
- **Neiman Marcus — Abb. Uomo — 1 oggetto — indossato — 1/6 — KITON**

→ The store generates one record per product brand sold there.

---

## Key Points

- The store/e-commerce record inherits **all classification decisions** from the product record (sub-line, value, tipo di comunicazione, objects, celebrities). Do not independently re-assess these for the store.
- Rule applies whether the item is **worn** (indossato) or shown as **product photo** (foto prodotto).
- If multiple product brands are cited at the same store on the same page, the store gets one separate record per product brand, each with the corresponding Marchio Commercializzato.
- The space value for the store record equals the space the product occupies — it does not get an additional or separate space; it "shadows" the product record.
