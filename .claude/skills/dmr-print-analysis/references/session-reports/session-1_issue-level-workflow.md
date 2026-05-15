# Print Data Entry (DMR) — Process Analysis

**Source:** Immersive session with Antonella Genovese & Francesca Boattini, recorded by Mariana Martella (date not recorded — prior to April 2026)

**Focus:** Issue-level workflow — from issue selection through page header creation.

---

## 1. End-to-End Workflow (Actions)

The data entry operator follows this sequence for each magazine issue:

1. **Navigate to "Inserimento Dati"** → **"Gestione Uscite"** (Issue Management).
2. **Select country** (e.g., Italy) — this filters the relevant publication list.
3. **Consult the priority file (Scadenza Testate)** — a dynamic deadline matrix managed under *Anagrafiche → Scadenza Testate* in Web Digital:
   - Publications grouped into **country groups** (e.g., Group A = Italy only, tighter deadlines). Currently 4 groups, fully configurable.
   - Deadlines differ by **periodicity** (daily vs. non-daily) and **priority tier** (P1, P2, P3).
   - Per combination, a **max calendar days** is set (e.g., P1 Italy = 7–10 days from arrival).
   - A separate **monthly closing deadline** per priority tier.
   - The matrix computes a **per-issue deadline date** (last column). Issues sorted by date; overdue rows turn **red**.
   - Fixed end-of-month rule to close all remaining items.
   - File owned/editable only by Francesca; operators read-only. Changes auto-recalculate all deadlines.
   - Team leads use it each morning to assign operators: some on overdue/red items, others on incoming P1s.
4. **Select the publication and issue** — e.g., *Elle Italia*, April 2026.
5. **Verify the issue is ready** — **"Fine Scansione"** flag must be present. The issue must have been physically received, registered (arrival date + source), and fully scanned.
6. **Enter the issue** — click **EDI** (editorial) or **ADV** (advertising). Roles enforced at user level.
7. **Set the cover image** — always C1, facciata = destra, positioning = "Prima di copertina". Click **"Imposta come immagine di copertina"** → yellow frame. Cover thumbnail propagates to all records.
8. **For each page, click the pencil icon** and fill in page header fields:
   - Regular editorial pages: all 6 fields mandatory (Numero pagina, Facciata, Posizionamento, Servizio/Rubrica, Titolo, Tipo di testo).
   - Special-positioning pages (cover, sommario, staff, editoriale, indirizzi): only top 3 fields required (Numero pagina, Facciata, Posizionamento).
9. **Save the page header** → system unlocks the full data-entry form.
10. **Repeat** for every page, following priority file order.

---

## 2. Key Points

| Area | Detail |
|---|---|
| **Priority system** | Three tiers (P1, P2, P3). P1 targets: 2–3 days. Deadlines computed by configurable matrix (country group × periodicity × priority tier). Francesca owns the matrix. |
| **Deadline file** | Rows turn red when overdue. Team leads redistribute operators each morning. P1 deadlines and previous-month spillover constantly intersect. |
| **Presumed issues** | System pre-creates future issues based on publication frequency. Semi-automatic — requires manual click ("Crea uscita presunta"). |
| **Scan dependency** | No data entry until magazine is received, registered, and scanned. Hard blocker. |
| **Role segregation** | EDI and ADV operators separated by user role to prevent cross-entry. |
| **Cover association** | Critical first step: cover thumbnail propagates to every record across DMR platforms. |
| **Page numbering** | Must match printed number. Unnumbered pages: count from C1. Uncounted inserts: "last-numbered-page + I + progressive" (e.g., 9.I1, 9.I2). Printing errors: alphabetical suffixes (A, B, C…) or "bis". |
| **Multiple covers** | Sequential covers, rotational covers, subscription-only, digital. All entered only if mentioned inside the magazine. Additional covers require scanning team ticket. |
| **Methodology is uniform** | Same rules across all brands/sectors. No LVMH-specific methodology for print. Differences only in number of brands tracked per publisher. |
| **Campaign identification (ADV only)** | Clients no longer send campaign PDFs. ADV teams search Modelcom independently — slower and error-prone. |
| **Quality bar** | Print error tolerance ~3%, far stricter than web/social. Clients rely on granular fields like "service type" for scoring. |

---

## 3. Pain Points

### A. Data Entry Complexity

| # | Pain Point | Impact |
|---|---|---|
| 1 | **Fully manual page-number entry** — operators type every page number, facciata, and positioning by hand. | Slow, error-prone, high repetition. |
| 2 | **Page-numbering anomalies** — uncounted pages, inserts, printing errors, mid-magazine supplements, Arabic RTL magazines. Every case requires manual judgment. | High cognitive load, no system guidance. |
| 3 | **Brand search from a huge list** — hundreds of sub-lines to scroll/search. | Major time sink on every page. |
| 4 | **Celebrity names typed manually** — no auto-suggest; must verify depicted vs. just mentioned. | Slow, inconsistent spelling. |
| 5 | **Value/space estimation is subjective** — 1/20 vs 1/15 vs 1/8 requires visual judgment, no measuring tool. | Inconsistency between operators. |
| 6 | **Service-type classification ambiguity** — beauty vs fashion is nuanced, complex, exception-heavy. | Even experienced operators disagree. |
| 7 | **No pre-population of any field** — every field starts blank. | Enormous repetitive typing. |

### B. Process / Procedure

| # | Pain Point | Impact |
|---|---|---|
| 8 | **Cover caption hunting** — credits may be in summary, editorial, "Cover Look", credits at back, or inside a fashion spread. | Double handling — operators often do entire magazine first, then return to cover. |
| 9 | **Multiple-cover detection** — must notice mentions inside magazine, open scanning ticket, attach proof, wait for collage. | Multi-step manual process, easy to miss. |
| 10 | **Campaign identification without client input (ADV)** — operators guess between RTW, bags, beauty, etc. | Misclassification risk. |

### C. Dependencies on Other Teams

| # | Pain Point | Impact |
|---|---|---|
| 11 | **Scan dependency as hard gate** — delayed scanning blocks operators even with magazine in hand. | Idle time, schedule compression. |
| 12 | **Multi-cover collage depends on scanning team** — ticket → scan → assemble → return. | Waiting time, communication overhead. |
| 13 | **Physical magazine reception depends on logistics** — foreign publications don't arrive daily. | Uneven workload, deadline pressure spikes. |

---

## 4. Easily Automatable Opportunities

### Quick wins (rule-based)

| # | Opportunity | How |
|---|---|---|
| A | **Auto-create presumed issues** | Bulk "crea uscita presunta" based on known periodicity. Already semi-implemented. |
| B | **Pre-fill cover metadata** | C1 is always C1, facciata=right, positioning="Prima di copertina". Auto-populate on issue open. |
| C | **Auto-assign facciata from page number** | Even=left, odd=right. Parity rule with Arabic inversion flag. |
| D | **Sequential page-number suggestion** | After page N, suggest N+1 (or N+2 for doubles). |

### Medium-term (OCR + text extraction)

| # | Opportunity | How |
|---|---|---|
| E | **Automatic page-number association** | OCR to detect printed numbers, auto-assign sequence, flag anomalies. |
| F | **Brand pre-suggestion via OCR** | Extract text, match against brand database, pre-populate. |
| G | **Celebrity name extraction** | OCR + NER on captions. Operator confirms depicted persons only. |
| H | **Section/rubrica recognition** | Match recurring headers against per-publication dictionary. |
| I | **Campaign matching for ads** | Image similarity or OCR against campaign database (Modelcom). |

### Longer-term (AI-assisted)

| # | Opportunity | How |
|---|---|---|
| J | **Product-category suggestion** | Image recognition for bags, RTW, shoes, jewelry, beauty. Human validation required. |
| K | **Space/value estimation** | Layout analysis to suggest proportional allocation. |
| L | **Multi-cover detection** | Keyword scan in summary/editorial for cover mentions. |

---

## 5. Strategic Takeaways from the Discussion

- **The realistic goal is acceleration, not replacement.** Full automation is unrealistic given exception density. Objective: shift operators from data entry to data validation.
- **Start with dailies (quotidiani).** Structurally simpler — ideal pilot for automation.
- **Pre-compilation is the first lever.** Simple field pre-population (brands, celebrities, sections) via OCR would already save significant time.
- **Quality control remains human.** Near-zero error tolerance means all automated output must be reviewed. QE team will continue.
- **Savings will take years.** Parallel human-review phase itself requires staffing.
