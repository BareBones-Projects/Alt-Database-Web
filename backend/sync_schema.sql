-- ALT Database v0.2 supplemental schema, safe to apply on existing v0.1 databases.
CREATE TABLE IF NOT EXISTS canon_changes (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT,
 entity_id TEXT NOT NULL,
 change_kind TEXT NOT NULL CHECK(change_kind IN ('upsert','withdraw')),
 visibility TEXT NOT NULL CHECK(visibility IN ('draft','public','restricted')),
 source_id TEXT,
 occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_canon_changes_entity ON canon_changes(entity_id,sequence);
CREATE TABLE IF NOT EXISTS canon_provenance (
 entity_id TEXT PRIMARY KEY REFERENCES entities(id),
 source_id TEXT NOT NULL,
 source_revision TEXT NOT NULL,
 source_record_id TEXT NOT NULL,
 source_sha256 TEXT NOT NULL,
 coordinate_frame TEXT,
 coordinate_unit TEXT,
 imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(source_id,source_record_id)
);
CREATE TABLE IF NOT EXISTS ingest_batches (
 batch_id TEXT PRIMARY KEY,
 source_id TEXT NOT NULL,
 file_sha256 TEXT NOT NULL,
 format TEXT NOT NULL,
 row_count INTEGER NOT NULL,
 imported_count INTEGER NOT NULL,
 skipped_count INTEGER NOT NULL,
 imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TRIGGER IF NOT EXISTS canon_changes_insert AFTER INSERT ON entities
BEGIN
 INSERT INTO canon_changes(entity_id,change_kind,visibility) VALUES(NEW.id,'upsert',NEW.visibility);
END;
CREATE TRIGGER IF NOT EXISTS canon_changes_update AFTER UPDATE ON entities
BEGIN
 INSERT INTO canon_changes(entity_id,change_kind,visibility) VALUES(NEW.id,
 CASE WHEN NEW.visibility='public' THEN 'upsert' ELSE 'withdraw' END,NEW.visibility);
END;
