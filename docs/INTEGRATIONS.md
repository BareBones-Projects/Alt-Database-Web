# // ALT Database integration map
Canonical data is written only by authenticated administrators. Consumer repos read versioned public API data and must not attempt to write the canonical DB.

| Repository | Responsibility | Suggested endpoint |
|---|---|---|
| alt-star-map-db | Source astronomy CSV import; display snapshots | GET /api/v1/entities?kind=star |
| GATE | Game/world locations and hex references | GET /api/v1/entities?kind=location |
| ALT-celestial-map-web | Browser map location catalogue | GET /api/v1/planets |
| ALT-celestial-map-unreal-engine | Runtime snapshot | GET /v1/map/snapshot |
| ALT-MarketGround | Public item/location metadata only, never inventory ownership | GET /api/v1/entities?kind=item |
| star-map-image-service | Image metadata, SHA-256, public media URLs | GET /api/v1/media |

**Important:** `/api/v1/planets` returns canonical entities, not the old bespoke five-planet layout shape. Consumers need an adapter. Local/mock fallback must be explicitly labeled noncanonical. Unreal navigation solver endpoints and web hex-cell endpoints are not yet implemented by this first milestone. Do not claim those clients are fully migrated.

## Data ownership and integrity
1. Import astronomical CSVs with explicit provenance, coordinate frame, unit, source revision and collision policy (future importer).
2. Use stable IDs across all repositories. Never infer coordinates from a UI layout.
3. Public read APIs exclude unpublished/draft/restricted records and media.
4. No media uploads or SQL migrations from public clients. Large media stored outside Git; SQL stores metadata and hash.
5. Preserve inventory authentication through the existing MarketGround/BareMark boundary. Public catalogue metadata is not a player entitlement.
6. Use HTTPS for all non-local clients, pin schema versions, and fail closed for admin paths.
7. Read API contract tests must pass in both central and consumer repos before replacing old providers.
