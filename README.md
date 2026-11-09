![ALT Database Web preview](assets/social-preview.svg)

# // ALT DATABASE WEB

Standalone **public website interface**, with all canonical content from [BareBones-Projects/ALT-Database-db](https://github.com/BareBones-Projects/ALT-Database-db). The website owns no database, credentials, SQL records or private exports.

**BareBones Projects, Designed by: Justin Levesque-Welsch.**

## Portals

- [Fandom DB](fandom-db/) — `/fandom-db/` — characters, factions and species.
- [Wiki DB](wiki-db/) — `/wiki-db/` — searchable public reference entries.
- [ALT DB](alt-db/) — `/alt-db/` — star systems, planets, districts, locations and navigation records.

All pages load records from the public read API: `GET /api/v1/entities`. The canonical backend also exposes `/api/v1/media` for approved public media metadata, and `/api/v1/health` for monitoring. The backend owns visibility filtering, authentication and all persistent writes. No sample data is presented as canonical.

## Setup

1. Run `python3 -m http.server 8080` from this repository and visit `http://localhost:8080/`.
2. Set `apiBaseUrl` in [config.js](config.js) to the public HTTPS API endpoint of the running **ALT-Database-db service**. Never set this to a GitHub repo URL or SQL URL, and never add secrets.
3. Enable the deployed web origin in the backend's public-read CORS allowlist.
4. Run `node --test tests/*.test.mjs` with Node.js 20+.

Without a live API URL the three portals remain clearly marked as disconnected, rather than pretending they contain real records.

## Public deployment

GitHub Pages publishes from `main` with [.github/workflows/pages.yml](.github/workflows/pages.yml). Select **GitHub Actions** under Repository Settings → Pages. The CI workflow runs tests on pull requests and commits. GitHub Pages requires a repository setting and can need organization policy approval. The deployment is not live until the workflow completes successfully.

## Assets

`assets/images/`, `assets/files/`, and `assets/previews/` are for reviewed static public uploads committed through Git. See [assets/README.md](assets/README.md). **Live browser uploads must use an authenticated backend or object storage.** GitHub Pages cannot securely receive them. Never commit unapproved assets, credentials or the database itself.

## Security

See [SECURITY.md](SECURITY.md). This repo is deliberately separate from the private database. Public clients only access public API endpoints, without credentials.

MIT licensed. © 2026 BareBones Projects.