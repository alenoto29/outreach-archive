-- Speed up case-insensitive email matching when importing large CSV files.
CREATE INDEX IF NOT EXISTS idx_journalists_email_lower ON journalists(lower(email));
INSERT INTO schema_version (version, description) VALUES (6, 'case-insensitive email lookup');
