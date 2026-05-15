-- DMR monitored-brands hierarchy
--
-- Source: dmr_monitored_brands.csv (denormalised export from upstream).
-- This schema normalises that export into the natural 4-level hierarchy:
--
--     holding ─< company ─< commercial_company ─< brand
--
-- Plus an `aliases` table that lets us index OCR-friendly variants
-- (case-folded, accent-stripped, "and"/"&" swaps, abbreviations, etc.)
-- without polluting the canonical-name columns.
--
-- The Aho-Corasick alias matcher loads its patterns from
--   SELECT alias_norm, entity_type, entity_id FROM aliases
-- so adding/removing aliases never requires touching code.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS holdings (
    id           INTEGER PRIMARY KEY,         -- HOLDING_ID from CSV
    name         TEXT    NOT NULL             -- canonical display name
);

CREATE TABLE IF NOT EXISTS companies (
    id           INTEGER PRIMARY KEY,         -- COMPANY_ID
    name         TEXT    NOT NULL,
    holding_id   INTEGER NOT NULL REFERENCES holdings(id)
);
CREATE INDEX IF NOT EXISTS idx_companies_holding ON companies(holding_id);

CREATE TABLE IF NOT EXISTS commercial_companies (
    id           INTEGER PRIMARY KEY,         -- COMMERCIAL_COMPANY_ID
    name         TEXT    NOT NULL,
    company_id   INTEGER NOT NULL REFERENCES companies(id)
);
CREATE INDEX IF NOT EXISTS idx_commcos_company ON commercial_companies(company_id);

CREATE TABLE IF NOT EXISTS brands (
    id                      INTEGER PRIMARY KEY,  -- BRAND_ID
    name                    TEXT    NOT NULL,
    commercial_company_id   INTEGER NOT NULL REFERENCES commercial_companies(id)
);
CREATE INDEX IF NOT EXISTS idx_brands_commco ON brands(commercial_company_id);

-- Aliases: one row per (entity, surface form). The canonical `name` of every
-- entity is also inserted here so the matcher only needs to scan one table.
--
--   entity_type ∈ ('HOLDING', 'COMPANY', 'COMMERCIAL_COMPANY', 'BRAND')
--   alias_raw   = the human-readable variant ("L'Oréal Paris")
--   alias_norm  = the lookup key produced by the same normaliser used at
--                 OCR-text time (lowercase, accents stripped, punctuation
--                 collapsed). NOT unique on its own because the same string
--                 can legitimately match multiple entities; tie-break in code.
--   source      = where the alias came from: 'canonical', 'manual',
--                 'ocr_variant', 'abbreviation', etc.
CREATE TABLE IF NOT EXISTS aliases (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type  TEXT    NOT NULL
                 CHECK (entity_type IN
                        ('HOLDING','COMPANY','COMMERCIAL_COMPANY','BRAND')),
    entity_id    INTEGER NOT NULL,
    alias_raw    TEXT    NOT NULL,
    alias_norm   TEXT    NOT NULL,
    source       TEXT    NOT NULL DEFAULT 'canonical',
    UNIQUE (entity_type, entity_id, alias_norm)
);
CREATE INDEX IF NOT EXISTS idx_aliases_norm        ON aliases(alias_norm);
CREATE INDEX IF NOT EXISTS idx_aliases_entity      ON aliases(entity_type, entity_id);

-- Convenience view: full chain for any brand, used when emitting
-- enriched Entity records into the pipeline output.
CREATE VIEW IF NOT EXISTS brand_chain AS
SELECT
    b.id            AS brand_id,
    b.name          AS brand,
    cc.id           AS commercial_company_id,
    cc.name         AS commercial_company,
    c.id            AS company_id,
    c.name          AS company,
    h.id            AS holding_id,
    h.name          AS holding
FROM brands b
JOIN commercial_companies cc ON cc.id = b.commercial_company_id
JOIN companies            c  ON c.id  = cc.company_id
JOIN holdings             h  ON h.id  = c.holding_id;
