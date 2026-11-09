# Security policy

BareBones Projects, Designed by: Justin Levesque-Welsch.

This is a public **static frontend repository**. Never add private API keys, user credentials, database exports, SQLite files, service-account keys, environment files or upload secrets.

All browser requests must use HTTPS public read endpoints with credentials omitted. The canonical backend is responsible for private/draft filtering, authorization, anti-abuse controls and database security. Set an exact public CORS allowlist in that backend.

GitHub Pages cannot securely accept user uploads. Stage only approved public assets in `assets/` via reviewed commits. For live uploading, use a separate authenticated upload endpoint, validated storage policy and approved object storage. Never place write credentials in web JavaScript.

For vulnerabilities, use private GitHub vulnerability reporting if enabled; do not post secrets to public issues.

Canonical backend: [ALT-Database-db](https://github.com/BareBones-Projects/ALT-Database-db).