# // ALT Database v0.2 · Canonical synchronization
Stage is stacked on **feature/sql-admin-hub-v0.1** (PR #2). Merge order matters; this branch is not based on alpha.

## Import policy
- Export CSV/JSON with explicit `id`, `kind`, `name` and optional `parent_id`, `data`, `source_record_id`.
- Default is dry-run, and every ingest is **draft** or **restricted**, never automatically public.
- Stable IDs must be agreed across repositories. A fixture does not gain canonical status because it appears in a README.
- Importer checks duplicates, source ownership, JSON structure, valid kinds and parent foreign keys. Inserts and updates are atomic.
- Specify a coordinate frame and unit for celestial data: `--frame ALT-GALACTIC-01 --unit ly`. This **does not convert coordinates**.
- Use `--conflict reject` (default), `skip` or `update` (update only if existing provenance belongs to the same source).
- Imported source provenance and SHA-256 hashes are recorded in SQL.
- Public visibility must be approved separately through the authenticated admin dashboard.

Example:
```bash
python backend/server.py init
python backend/import_canon.py data/sample-import.json --db runtime/alt.sqlite3 --source alt-star-map-db --revision batch-1 --frame ALT-GALACTIC-01 --unit ly
python backend/import_canon.py data/sample-import.json --db runtime/alt.sqlite3 --source alt-star-map-db --revision batch-1 --frame ALT-GALACTIC-01 --unit ly --apply
```

## Read contracts
- `GET /api/v1/changes?since=0`: monotonically increasing global sequence (public IDs plus withdrawal notices).
- `GET /api/v1/hex-cells/{id}/contents`: current public hex-linked entities, no fabricated routes.
- `GET /v1/map/snapshot`: public canonical entity snapshot; still requires client-specific format validation.
- `GET /api/v1/planets`: canonical entity envelope, not existing viewer layout data.
- Private IDs and draft changes are omitted from the public feed.

## Production hold points
Importer supports explicit standard records; it does NOT directly assume a 45,000-body astronomy CSV format, handle heavy media, solve navigation routes, stream large result pages, or perform physical coordinate transforms. Integration tests and production access controls are still required.
