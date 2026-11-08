PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS entities (
 id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('star','planet','moon','system','location','hex','route','character','faction','item','lore')),
 name TEXT NOT NULL, parent_id TEXT REFERENCES entities(id), visibility TEXT NOT NULL DEFAULT 'draft' CHECK(visibility IN ('draft','public','restricted')),
 data_json TEXT NOT NULL DEFAULT '{}', revision INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_entities_kind_visibility ON entities(kind,visibility);
CREATE TABLE IF NOT EXISTS media (
 id TEXT PRIMARY KEY, entity_id TEXT REFERENCES entities(id), filename TEXT NOT NULL, mime TEXT NOT NULL, bytes INTEGER NOT NULL,
 sha256 TEXT NOT NULL, storage_path TEXT NOT NULL, visibility TEXT NOT NULL DEFAULT 'draft' CHECK(visibility IN ('draft','public','restricted')),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS admins (
 username TEXT PRIMARY KEY, salt TEXT NOT NULL, password_hash TEXT NOT NULL, iterations INTEGER NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash TEXT PRIMARY KEY, username TEXT NOT NULL REFERENCES admins(username), expires_at INTEGER NOT NULL, csrf_token TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
 id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, action TEXT NOT NULL, target TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ingest_sources (
 source_id TEXT PRIMARY KEY, repo TEXT NOT NULL UNIQUE, last_revision TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);