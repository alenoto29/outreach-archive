-- Migration 004: Add UK and PT markets to publishers, journalists, campaigns
-- SQLite does not support ALTER TABLE DROP CONSTRAINT, so we recreate tables.

PRAGMA foreign_keys=OFF;
BEGIN;

-- ── Publishers ─────────────────────────────────────────────────────────
CREATE TABLE publishers_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    domain TEXT,
    dr INTEGER CHECK(dr IS NULL OR (dr >= 0 AND dr <= 100)),
    publisher_scope TEXT,
    media_group TEXT,
    media_type TEXT,
    market TEXT NOT NULL CHECK(market IN ('IT','ES','FR','UK','PT')),
    region TEXT,
    editorial_team_url TEXT,
    twitter_handle TEXT,
    enrichment_last_scraped TEXT,
    enrichment_source TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    updated_by TEXT,
    deleted_at TEXT,
    UNIQUE(name, market)
);
INSERT INTO publishers_new SELECT * FROM publishers;
DROP TABLE publishers;
ALTER TABLE publishers_new RENAME TO publishers;

CREATE INDEX idx_publishers_market ON publishers(market) WHERE deleted_at IS NULL;
CREATE INDEX idx_publishers_dr ON publishers(dr) WHERE deleted_at IS NULL;
CREATE INDEX idx_publishers_name ON publishers(name) WHERE deleted_at IS NULL;

-- ── Journalists ──────────────────────────────────────────────────────────
CREATE TABLE journalists_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL CHECK(email LIKE '%@%'),
    first_name TEXT,
    last_name TEXT,
    job_title TEXT,
    publisher_id INTEGER REFERENCES publishers(id),
    market TEXT NOT NULL CHECK(market IN ('IT','ES','FR','UK','PT')),
    email_type TEXT,
    email_status TEXT,
    response_status TEXT,
    linkedin TEXT,
    author_page TEXT,
    twitter TEXT,
    phone TEXT,
    main_topic TEXT,
    priority TEXT,
    notes TEXT,
    linkedin_status TEXT,
    contacted_by TEXT,
    linkedin_conversation TEXT,
    contact_count INTEGER DEFAULT 0,
    authority TEXT,
    last_contacted TEXT,
    weeks_since_contact INTEGER,
    reports_count INTEGER DEFAULT 0,
    enrichment_status TEXT,
    enrichment_last_scraped TEXT,
    enrichment_bio TEXT,
    years_exp INTEGER,
    last_article_date TEXT,
    articles_count_6m INTEGER,
    expertise_tags TEXT,
    enrichment_source TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    updated_by TEXT,
    deleted_at TEXT
);
INSERT INTO journalists_new SELECT * FROM journalists;
DROP TABLE journalists;
ALTER TABLE journalists_new RENAME TO journalists;

CREATE INDEX idx_journalists_email ON journalists(email);
CREATE INDEX idx_journalists_publisher ON journalists(publisher_id);
CREATE INDEX idx_journalists_market ON journalists(market) WHERE deleted_at IS NULL;
CREATE INDEX idx_journalists_response_status ON journalists(response_status) WHERE deleted_at IS NULL;

-- ── Campaigns ───────────────────────────────────────────────────────────
CREATE TABLE campaigns_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    market TEXT NOT NULL CHECK(market IN ('IT','ES','FR','UK','PT')),
    date_start TEXT,
    date_end TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    updated_by TEXT,
    deleted_at TEXT,
    UNIQUE(name, market)
);
INSERT INTO campaigns_new SELECT * FROM campaigns;
DROP TABLE campaigns;
ALTER TABLE campaigns_new RENAME TO campaigns;

CREATE INDEX idx_campaigns_market ON campaigns(market) WHERE deleted_at IS NULL;

-- Re-enable foreign keys
COMMIT;
PRAGMA foreign_keys=ON;

INSERT INTO schema_version (version, description) VALUES (4, 'add UK and PT markets');