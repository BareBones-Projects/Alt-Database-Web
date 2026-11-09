# Public asset staging

BareBones Projects, Designed by: Justin Levesque-Welsch.

- `images/`: approved optimized JPG, PNG, WebP, AVIF and SVG illustrations.
- `files/`: approved public downloadable documents.
- `previews/`: small compressed thumbnails, generated previews and social images.
- `social-preview.svg`: source-controlled share art.

**These are Git-managed deployment assets, not an open upload destination.** Do not put raw masters, private lore, personal files, or database exports in this repository. Keep large originals and live uploads in authenticated object storage or the private database service. The public UI reads approved media metadata from `GET /api/v1/media`. For actual live upload, configure an authenticated upload service and validated object-store pipeline on the database side, including file signature/MIME checks, size caps, antivirus scanning, UUID filenames, authorization, and moderation. Never expose object-store write keys in browser JavaScript.