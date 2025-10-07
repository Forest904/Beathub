## Data Contracts Overview

This project relies on a small set of cross-layer contracts between the
download pipeline, Flask APIs, and the React UI. The goal of this document is
to centralise those expectations so future changes remain compatible.

### Download Items (`/api/albums`)

- **Source:** `DownloadedItem` rows persisted by the orchestrator.
- **Frontend mapper:** `toDownloadItem` in `frontend/src/api/mappers.js`.
- **Required fields:** `id`, `spotify_id`, `name`, `title`, `artist`,
  `image_url`, `spotify_url`, `local_path`, `is_favorite`, `item_type`.
- The frontend treats `name` as the primary display value. The mapper now
  normalises backend payloads so legacy responses (which only had `title`)
  still populate `name`.

### Download Jobs (`/api/download/jobs/<id>`)

- **Source:** `DownloadJob` SQLAlchemy model.
- **Guaranteed fields:** `id`, `user_id`, `link`, `status`, `result`, `error`,
  `created_at`, `updated_at`.
- Consumers should expect `result` to be a dictionary mirroring the download
  response when `status === "completed"`, or `None` otherwise.

### Album Card Inputs (shared UI component)

- The shared `AlbumCard` component accepts `name`, `artist`, `title`,
  `image_url`, and `spotify_url`. It gracefully falls back to `title` when
  `name` is absent and hides the subtitle when both `artist` and `title` are
  missing.
- Any new data source feeding album-like objects into the UI should either
  provide `name` directly or reuse the existing mapper helpers to inherit the
  normalisation logic.

### Change Guidelines

1. Prefer extending mappers or DTOs rather than mutating raw API responses.
2. If a contract-breaking change is unavoidable, version the endpoint or add
   backward-compatible fields and update this document.
3. Unit or integration tests that assert these shapes should accompany future
   contract changes.

