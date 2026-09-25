-- Migration 001: initial schema
-- Source of truth: ../schema.sql
-- Applied via: sqlite3 db.sqlite < migrations/001_initial.sql

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

CREATE TABLE publishers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    domain TEXT,
    dr INTEGER CHECK(dr IS NULL OR (dr >= 0 AND dr <= 100)),
    publisher_scope TEXT,
    media_group TEXT,
    media_type TEXT,
    market TEXT NOT NULL CHECK(market IN ('IT','ES','FR')),
    region TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    updated_by TEXT,
    deleted_at TEXT,
    UNIQUE(name, market)
);
CREATE INDEX idx_publishers_market ON publishers(market) WHERE deleted_at IS NULL;
CREATE INDEX idx_publishers_dr ON publishers(dr) WHERE deleted_at IS NULL;
CREATE INDEX idx_publishers_name ON publishers(name) WHERE deleted_at IS NULL;

CREATE TABLE journalists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL CHECK(email LIKE '%@%'),
    first_name TEXT,
    last_name TEXT,
    job_title TEXT,
    publisher_id INTEGER REFERENCES publishers(id),
    market TEXT NOT NULL CHECK(market IN ('IT','ES','FR')),
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
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    updated_by TEXT,
    deleted_at TEXT
);
CREATE INDEX idx_journalists_email ON journalists(email);
CREATE INDEX idx_journalists_publisher ON journalists(publisher_id);
CREATE INDEX idx_journalists_market ON journalists(market) WHERE deleted_at IS NULL;
CREATE INDEX idx_journalists_response_status ON journalists(response_status) WHERE deleted_at IS NULL;

CREATE TABLE topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE journalist_topics (
    journalist_id INTEGER NOT NULL REFERENCES journalists(id) ON DELETE CASCADE,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    source TEXT NOT NULL CHECK(source IN ('csv','inferred','manual')),
    PRIMARY KEY (journalist_id, topic_id, source)
);
CREATE INDEX idx_jt_journalist ON journalist_topics(journalist_id);
CREATE INDEX idx_jt_topic ON journalist_topics(topic_id);

CREATE TABLE campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    market TEXT NOT NULL CHECK(market IN ('IT','ES','FR')),
    date_start TEXT,
    date_end TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    updated_by TEXT,
    deleted_at TEXT,
    UNIQUE(name, market)
);
CREATE INDEX idx_campaigns_market ON campaigns(market) WHERE deleted_at IS NULL;

CREATE TABLE journalist_campaigns (
    journalist_id INTEGER NOT NULL REFERENCES journalists(id) ON DELETE CASCADE,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (journalist_id, campaign_id)
);

CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    journalist_id INTEGER NOT NULL REFERENCES journalists(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    date TEXT,
    topics_inferred TEXT,
    scraped_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_articles_journalist ON articles(journalist_id);
CREATE UNIQUE INDEX idx_articles_url ON articles(url);

CREATE TABLE reports_sent (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    journalist_id INTEGER NOT NULL REFERENCES journalists(id) ON DELETE CASCADE,
    report_name TEXT NOT NULL,
    sent_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_reports_journalist ON reports_sent(journalist_id);

CREATE TABLE outreach_sends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    journalist_id INTEGER REFERENCES journalists(id) ON DELETE SET NULL,
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
    strategy TEXT,
    email_subject TEXT,
    email_body TEXT,
    sent_at TEXT NOT NULL,
    sent_by TEXT,
    status TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_outreach_journalist ON outreach_sends(journalist_id);
CREATE INDEX idx_outreach_campaign ON outreach_sends(campaign_id);
CREATE INDEX idx_outreach_sent_at ON outreach_sends(sent_at);

CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL CHECK(entity_type IN ('journalist','publisher','campaign','outreach_send','article','topic')),
    entity_id INTEGER NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('create','update','delete','restore')),
    field TEXT,
    old_value TEXT,
    new_value TEXT,
    user TEXT NOT NULL,
    role TEXT,
    ts TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_ts ON audit_log(ts);
CREATE INDEX idx_audit_user ON audit_log(user);

INSERT INTO schema_version (version, description) VALUES (1, 'initial schema');
