-- Publication-level summary: pages (editorial vs advertising), distinct brands /
-- products / persons, and total mentions of each. The latest_run_per_page CTE
-- collapses re-runs of the same input file to the most recent row so re-running
-- a publication doesn't double-count.
--
-- Run with:
--   sqlite3 -header -column database/results.db < scripts/publication_analysis.sql

WITH latest_run_per_page AS (
    SELECT r.id AS run_id, r.publication_id, r.input_file
    FROM runs r
    WHERE r.publication_id IS NOT NULL
      AND r.id = (
          SELECT MAX(r2.id) FROM runs r2
          WHERE r2.publication_id = r.publication_id
            AND r2.input_file    = r.input_file
      )
),
page_stats AS (
    SELECT
        lr.publication_id,
        COUNT(*) AS total_pages,
        SUM(CASE WHEN pg.classification = 'editorial'   THEN 1 ELSE 0 END) AS editorial_pages,
        SUM(CASE WHEN pg.classification = 'advertising' THEN 1 ELSE 0 END) AS advertising_pages
    FROM latest_run_per_page lr
    JOIN pages pg ON pg.run_id = lr.run_id
    GROUP BY lr.publication_id
),
entity_stats AS (
    SELECT
        lr.publication_id,
        COUNT(DISTINCT CASE WHEN e.label = 'BRAND'   THEN e.text END) AS distinct_brands,
        SUM(CASE WHEN e.label = 'BRAND'   THEN 1 ELSE 0 END)          AS brand_mentions,
        COUNT(DISTINCT CASE WHEN e.label = 'PRODUCT' THEN e.text END) AS distinct_products,
        SUM(CASE WHEN e.label = 'PRODUCT' THEN 1 ELSE 0 END)          AS product_mentions,
        COUNT(DISTINCT CASE WHEN e.label = 'PERSON'  THEN e.text END) AS distinct_persons,
        SUM(CASE WHEN e.label = 'PERSON'  THEN 1 ELSE 0 END)          AS person_mentions
    FROM latest_run_per_page lr
    JOIN pages       pg ON pg.run_id        = lr.run_id
    JOIN text_blocks tb ON tb.page_id       = pg.id
    JOIN entities    e  ON e.text_block_id  = tb.id
    GROUP BY lr.publication_id
)
SELECT
    p.magazine_name,
    p.issue_date,
    p.name AS publication_folder,
    COALESCE(ps.total_pages,        0) AS total_pages,
    COALESCE(ps.editorial_pages,    0) AS editorial_pages,
    COALESCE(ps.advertising_pages,  0) AS advertising_pages,
    COALESCE(es.distinct_brands,    0) AS distinct_brands,
    COALESCE(es.brand_mentions,     0) AS brand_mentions,
    COALESCE(es.distinct_products,  0) AS distinct_products,
    COALESCE(es.product_mentions,   0) AS product_mentions,
    COALESCE(es.distinct_persons,   0) AS distinct_persons,
    COALESCE(es.person_mentions,    0) AS person_mentions
FROM publications p
LEFT JOIN page_stats   ps ON ps.publication_id = p.id
LEFT JOIN entity_stats es ON es.publication_id = p.id
ORDER BY p.magazine_name, p.issue_date;
