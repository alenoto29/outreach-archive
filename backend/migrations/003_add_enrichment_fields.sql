-- 003_add_enrichment_fields.sql
-- Add optional source-attributed enrichment metadata.
-- Applicare manualmente: sqlite3 backend/db.sqlite < backend/migrations/003_add_enrichment_fields.sql

-- Journalists: nuovi campi enrichment (linkedin/twitter/enrichment_bio/enrichment_status/enrichment_last_scraped gia' esistono)
ALTER TABLE journalists ADD COLUMN years_exp INTEGER;
ALTER TABLE journalists ADD COLUMN last_article_date TEXT;
ALTER TABLE journalists ADD COLUMN articles_count_6m INTEGER;
ALTER TABLE journalists ADD COLUMN expertise_tags TEXT;  -- JSON array
ALTER TABLE journalists ADD COLUMN enrichment_source TEXT;  -- 'exa' | 'manual' | 'scrape'

-- Publishers: nuovi campi
ALTER TABLE publishers ADD COLUMN editorial_team_url TEXT;
ALTER TABLE publishers ADD COLUMN twitter_handle TEXT;
ALTER TABLE publishers ADD COLUMN enrichment_last_scraped TEXT;
ALTER TABLE publishers ADD COLUMN enrichment_source TEXT;

INSERT INTO schema_version (version, description) VALUES (3, 'add enrichment fields for exa pipeline');
