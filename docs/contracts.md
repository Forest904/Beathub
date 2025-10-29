# Data Contracts

This document records the JSON payloads shared between the Flask API and the React frontend. Keep it up to date whenever response shapes or request bodies change so the UI and automated tests remain in sync.

## Download Items (`/api/albums`, `/api/download/items/...`)

`DownloadedItem` records are serialised with the following fields:

| Field | Type | Notes |
| --- | --- | --- |
| `id` | integer | Internal primary key. |
| `spotify_id` | string | Spotify identifier or synthetic id for compilations. |
| `item_type` | string | One of `album`, `track`, `playlist`, `compilation`. |
| `title` | string | Display title (album/playlist/track name). |
| `artist` | string | Album artist or track artist. |
| `image_url` | string? | Usually an API path pointing at `/api/items/by-spotify/<id>/cover`. |
| `spotify_url` | string? | Original Spotify link if available. |
| `local_path` | string? | Absolute path to the download directory (used by backend utilities). |
| `is_favorite` | boolean | True if the item is favourited. |

The frontend normalises responses so `name` falls back to `title`. Avoid removing existing keys; add new ones alongside these defaults.

## Download Jobs (`/api/download/jobs/<id>`)

Download jobs represent asynchronous spotDL executions queued by `JobQueue`.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | UUID generated when queued. |
| `user_id` | integer | Owner of the job. |
| `link` | string | Original Spotify link submitted. |
| `status` | string | `pending`, `running`, `completed`, `failed`, `cancelled`. |
| `result` | object? | Mirrors the orchestrator response on success. `null` until finished. |
| `error` | string? | Friendly error message when `status` is `failed`. |
| `created_at` / `updated_at` | ISO8601 string | Timestamps in UTC. |

## Playlist API (`/api/playlists/*`)

### Playlist object

| Field | Type | Notes |
| --- | --- | --- |
| `id` | integer | Playlist id. |
| `user_id` | integer | Owner. |
| `name` | string | Playlist title. |
| `description` | string? | Optional description. |
| `created_at` / `updated_at` | ISO8601 string | Audit timestamps. |
| `track_count` | integer | Number of entries. |
| `tracks` | array | Only returned when `include_tracks` is requested (default for CRUD endpoints except list). |

### Playlist track entry

| Field | Type | Notes |
| --- | --- | --- |
| `id` | integer | Playlist entry id. |
| `playlist_id` | integer | Owning playlist. |
| `track_id` | integer | Foreign key to `DownloadedTrack`. |
| `position` | integer | Zero-based ordering. |
| `added_at` | ISO8601 string | When the entry was created. |
| `track` | object | Snapshot of the downloaded track (contains `title`, `artists`, `spotify_id`, `cover_url`, etc.). |

Payload expectations:

- `POST /api/playlists` accepts `{ "name": string, "description"?: string, "tracks"?: TrackInput[] }`.
- `POST /api/playlists/<id>/tracks` accepts `{ "tracks": TrackInput[] }` (array or single object). Each `TrackInput` needs at minimum `spotify_id` (or `id`) and `title`.
- `PUT /api/playlists/<id>` can replace the full track list by providing `tracks`.

## Favourites API (`/api/favorites/*`)

`Favorite` objects are returned as:

| Field | Type | Notes |
| --- | --- | --- |
| `id` | integer | Favourite id. |
| `user_id` | integer | Owner. |
| `item_type` | string | One of `artist`, `album`, `track`. |
| `item_id` | string | Spotify id. |
| `item_name` | string | Display name. |
| `item_subtitle` | string? | Secondary text (e.g. artist name). |
| `item_image_url` | string? | Thumbnail URL if available. |
| `item_url` | string? | External link (Spotify URL). |
| `created_at` | ISO8601 string | Created timestamp. |

`GET /api/favorites/summary` returns `{ "summary": { "artist": int, "album": int, "track": int, "total": int } }` with missing categories defaulted to zero.

## Settings API (`/api/settings/*`)

### Runtime download settings (`GET /api/settings/download`)

Response shape:

```json
{
  "settings": {
    "base_output_dir": "downloads",
    "threads": 2,
    "preload": false,
    "simple_tui": false
  },
  "defaults": { ...same shape... },
  "api_keys": {
    "spotify_client_id": {"configured": true},
    "spotify_client_secret": {"configured": true},
    "genius_access_token": {"configured": false}
  },
  "spotdl_ready": true,
  "spotify_ready": true,
  "genius_ready": false,
  "credentials_ready": true
}
```

- `settings` is the active runtime configuration after overrides.
- `defaults` reflect baseline values derived from `.env`/`Config`.
- `api_keys` omits secrets and only signals configuration status and last-updated timestamps.

### Update download settings (`PUT /api/settings/download`)

Request body accepts either the wrapped form used by the UI or flat keys:

```json
{
  "download": {
    "base_output_dir": "D:/Music",
    "threads": 4,
    "preload": true
  },
  "api_keys": {
    "spotify_client_id": "...",
    "spotify_client_secret": "...",
    "genius_access_token": null
  }
}
```

Returning payload matches the `GET` response once persisted. Passing `null` for an API key deletes the stored value.

### Settings status (`GET /api/settings/status`)

Returns the readiness flags plus redacted API key state; same fields as `GET /api/settings/download` without the `settings`/`defaults` objects.

## Progress Stream (`/api/progress/stream`)

SSE frames contain JSON payloads published by downloads or CD burning. Common keys:

| Field | Description |
| --- | --- |
| `event` | Logical event type (`download_progress`, `download_complete`, `cd_burn_progress`, etc.). |
| `status` | Human friendly status message. |
| `progress` | Integer percentage for the current phase. |
| `overall_completed` / `overall_total` | Progress counters for multi-track downloads. |
| `failed_tracks` | Array of track identifiers when errors occur. |
| `session_id` | Present for CD burning events. |

Heartbeats are emitted as `event: heartbeat` every ~15 seconds to keep connections alive.

## CD Burning Sessions (`/api/cd-burner/status`)

Burn session payloads come from `BurnSession.to_dict()` and include:

| Field | Description |
| --- | --- |
| `id` | Session id generated server-side. |
| `title` | Item currently being burned. |
| `is_burning` | Whether a burn is in progress. |
| `progress_percentage` | Overall progress (0-100). |
| `phase` | One of `preparing`, `converting`, `staging`, `burning`, `completed`, `error`. |
| `message` | Latest status message. |
| `error` | Present when the burn failed. |
| `history` | Array of timestamped log events for UI timelines. |

## Error Conventions

- Validation failures return `400` with `{ "errors": { "field": "reason" } }`.
- Authentication issues return `401` with `{ "error": "authentication_required" }`.
- Permission or state conflicts use `409` with `{ "error": "..." }`.
- Backend failures log the exception and respond with `500` plus `{ "error": "message" }`.
