# // ALT DATABASE

Canonical SQL lore, navigation records, images and media metadata for BareBones Projects.

## Quick start

Python 3.11+; no third-party dependencies.

```bash
python backend/server.py init
python backend/server.py create-admin --username admin
ALT_COOKIE_SECURE=0 python backend/server.py serve --host 127.0.0.1 --port 8090
python -m unittest discover -s tests -p 'test_*.py' -v
```

Open http://127.0.0.1:8090/login. **Only set ALT_COOKIE_SECURE=0 on localhost.** Production requires HTTPS, private persistent volumes, rate limiting and security review. To allow browser reads from an explicitly trusted cross-origin map frontend, set `ALT_PUBLIC_ORIGINS=https://your-map-host.example` (comma-separated exact origins); no admin route gets CORS access. Never publish the runtime directory or .sqlite3 files.

## Components

- `backend/schema.sql`: SQLite canonical entity records, media, admins, sessions, audit trail and ingest provenance.
- `backend/server.py`: API and admin-only authenticated record editing.
- `admin/`: gated dashboard, login and media manager.
- `tests/`: smoke and schema tests.
- `docs/INTEGRATIONS.md`: six downstream repositories, endpoint mappings and migration guidance.
- `.github/workflows/database-ci.yml`: Python CI for PRs.

## Public read API

`GET /api/v1/health`, `/api/v1/entities`, `/api/v1/planets`, `/api/v1/objects/{id}`, `/api/v1/media`, `/api/v1/media/{id}`, `/v1/map/snapshot` and `/v1/objects/{id}`.

Only `public` visibility content is exposed. Admin routes use HttpOnly SameSite sessions, PBKDF2 password hashes and an X-CSRF-Token for writes. No registration endpoint exists. Maximum inline media upload is 8 MiB; use object storage for large video and image masters. SQL migrations are reviewed code, not browser uploads.

## Branch workflow

Make a feature branch from `alpha`, run local tests, open a PR and wait for checks. Keep clients backward-compatible and do not grant them SQL write credentials. This version establishes the hub; Unreal navigation solver, web hex-cell data and bulk CSV ingestion require later compatibility work before full production migration.

MIT license. Copyright (c) 2026 BareBones Projects.

## v0.2 canonical synchronization (draft PR #3)
The next-stage importer supports validated CSV/JSON records with stable IDs, source revision, SHA-256 provenance, collision policies, and atomic draft-only ingestion. The public API adds `/api/v1/changes?since=0` and `/api/v1/hex-cells/{id}/contents`.

```bash
python backend/server.py init
python scripts/convert_star_map_csv.py path/to/cyclus.csv --output runtime/star-candidates.json
python backend/import_canon.py runtime/star-candidates.json --db runtime/alt.sqlite3 --source alt-star-map-db --revision batch-1
# Review the dry-run report before adding --apply
python backend/import_canon.py runtime/star-candidates.json --db runtime/alt.sqlite3 --source alt-star-map-db --revision batch-1 --apply
```

Imported records are **not published** until approved by an authenticated administrator. Conversion of source coordinates does not imply survey verification. See [canonical sync specification](docs/CANONICAL_SYNC_V0.2.md).
