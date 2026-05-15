# Print Data Entry (DMR) — Timing Analysis Report

**Source:** Database export (RECORD.DATEINS) — Marie Claire, Issue ID 10810796, 1 April 2026 issue  
**Operator:** CREATEDBY = 345  
**Sessions:** 26 March 2026 (10:43–15:56) · 27 March 2026 (07:27–10:33)  
**Analysis produced by:** Mariana Martella, 16 April 2026

---

## Overview

This report quantifies the time spent on data enrichment actions for a single issue of Marie Claire. It is based on the `RECORD.DATEINS` field, which timestamps each record insertion. Each row in the export represents one enrichment action (one record saved) on a given page (`NUMBER`). The delta between consecutive actions (sorted by timestamp) is used as a proxy for the time the operator spent on each action.

**Methodology:**
- Data sorted by insertion timestamp ascending.
- Delta = time between current record and the immediately following record in global order.
- 2 cross-day records removed (last record of 26 Mar, last record of 27 Mar) as their delta spans the overnight break and is not attributable to actual work time.
- Records with delta > 1,000 min excluded from the average calculation (1 record: the overnight gap between the two sessions).
- **Average time per action = total valid time ÷ number of valid records.**

---

## 1. Key Metrics

| Metric | Value |
|---|---|
| **Records analysed** | 359 (after removing 2 cross-day boundary records from 361 raw) |
| **Distinct pages (NUMBER)** | 81 pages |
| **Total valid work time** | 1,430 min (23.8 hours across 2 days) |
| **⏱ Average time per action** | **4.00 min (240 sec)** |
| **Median delta between actions** | 0.39 min (24 sec) |
| **Session 1 — 26 Mar** | 254 records · 10:43–15:56 · avg 4.90 min/action |
| **Session 2 — 27 Mar** | 105 records · 07:27–10:33 · avg 1.79 min/action |

> **Note on mean vs. median:** The mean (4.00 min) is pulled upward by a small number of long gaps (pauses, lunch). The median (24 sec) reflects the typical pace of back-to-back data entry actions. Both are reported because they measure different things: median = typical action speed; mean = average cost per record including all interruptions.

---

## 2. Distribution of Action Deltas

| Delta range | Count | % of records | Interpretation |
|---|---|---|---|
| < 1 min | 272 | 76% | Rapid actions: duplications, sequential field saves, copy-paste entries |
| 1–5 min | 67 | 19% | Standard single-record data entry |
| 5–30 min | 16 | 4% | Complex pages (contextualization, many brands) or brief interruptions |
| > 30 min | 3 | 1% | Lunch break / extended pause |
| > 1,000 min | 1 | — | Overnight gap (excluded from average) |

The 76% of actions under 1 minute confirms that operators spend most of their time in rapid sequential mode — suggesting the workflow is heavily optimized for speed on "simple" pages, with a long tail of harder pages pulling the average up.

---

## 3. Per-Page Analysis — Key Findings

### Pages with most records (most complex)

| Page (NUMBER) | Records | Duration (min) | Avg Δ within page (min) |
|---|---|---|---|
| 36 | 14 | 14.2 | 1.09 |
| 39 | 13 | 7.3 | 0.61 |
| 125 | 11 | 102.1 | 10.21 |
| 165 | 10 | 4.0 | 0.44 |
| 172 | 10 | 7.1 | 0.79 |

### Pages with longest total duration (excluding cross-day anomalies)

| Page (NUMBER) | Records | Duration (min) |
|---|---|---|
| 125 | 11 | 102.1 |
| 126 | 3 | 97.1 |
| 127 | 8 | 96.0 |
| 128 | 8 | 92.6 |
| 129 | 3 | 88.8 |

Pages 125–145 (worked during 14:29–15:47 on 26 Mar) all show durations of 45–102 min, but this is an artifact of the grouping method: their `first_ts` and `last_ts` are on the same day but span the broader session window. Multiple pages were worked in parallel (overlapping timestamps), so individual page duration is not the same as net time spent.

### Pages worked in parallel (overlapping timestamps)

Negative "gap to next NUMBER" values (visible in the full table) indicate pages worked concurrently — the operator moved between pages without completing one before starting another. This is expected behaviour for pages within the same fashion story or contextual block.

### Single-record pages

19 of 81 pages have only one record (single brand, single space entry). These average under 1 min per page in practice and represent the simplest data entry case.

---

## 4. Observations & Implications

### A. Pace difference between sessions

Session 2 (27 Mar, 1.79 min/action) is significantly faster than Session 1 (4.90 min/action). Possible explanations:
- Session 2 may have involved simpler pages (fewer brands, no contextualization)
- Familiarity with the issue content after Session 1
- Session 2 includes a block of rapid saves at 10:33 (9 records in 15 seconds for NUMBER 20), suggesting a bulk correction or duplication pass rather than manual entry

### B. The 24-second median is a useful baseline

For pages with straightforward content (single brand, known sub-line, standard tipo di comunicazione), an experienced operator saves one record every ~24 seconds. Any automation that reduces even 2–3 fields per record could meaningfully compress this baseline.

### C. Long-duration pages concentrate in a contiguous block

Pages 125–145 were worked between 14:29 and 15:47, and most have durations >45 min when measured as (last\_ts − first\_ts). This reflects a fashion story with many brands worked on simultaneously. For timing purposes, the within-page delta average is more informative than total duration for these pages.

### D. 19 single-record pages suggest fast-track potential

Pages with a single record have no ambiguity (no competing brands, no contextualization). These could benefit most from pre-fill automation (season, tipo di comunicazione based on page type).

---

## 5. Data Notes

- **Cross-day NUMBERs:** c1b and 26 appear in both sessions. Their `duration_min` in the summary table reflects (last\_ts − first\_ts) across both days (~1,288 min each) and should be ignored for duration analysis. Their within-session record counts and intra-page deltas are unaffected.
- **Source query:** `SELECT RECORD.DATEINS, PAGE.NUMBER FROM PAGE INNER JOIN RECORD ON PAGE.ID = RECORD.PAGEID WHERE ISSUEID = 10810796 AND PAGE.ACTIVE = 1 AND RECORD.ACTIVE = 1 AND PAGE.ADV = 0 AND RECORD.CREATEDBY = 345 ORDER BY RECORD.DATEINS ASC`
- **Output file:** `MARIE_CLAIRE_analisi_tempi.xlsx` (3 sheets: Key Metrics · Riepilogo per Pagina · Dati Dettaglio)
