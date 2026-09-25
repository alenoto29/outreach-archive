-- Migration 005: add url_canonical column for dedup across protocol/www/query-string variants.
-- (Renumbered from 004 — collided with 004_add_uk_pt_markets on schema_version.version,
--  which can otherwise cause this migration to be skipped when migration 004 runs first.)
-- Existing rows keep url_canonical NULL; backfill via tools/backfill_article_canonical.py.
-- New inserts (articles.py add_articles) populate it.
-- Guard ALTER so a re-apply on a DB that already has the column doesn't abort the file.

ALTER TABLE articles ADD COLUMN url_canonical TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_url_canonical
    ON articles(url_canonical) WHERE url_canonical IS NOT NULL;

INSERT INTO schema_version (version, description) VALUES (5, 'add url_canonical column + partial unique index');
