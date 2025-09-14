# Refactor to SpotDL Service Architecture — Roadmap

This document tracks the migration from spotDL CLI subprocess calls to the SpotDL Python API, keeping the current Flask API and React frontend. Work happens on branch `refactor/spotdl-service`.

## Phase 0 — Branch & Safety
- [x] Create branch `refactor/spotdl-service`
- [x] Add feature flag `USE_SPOTDL_PIPELINE` (default: false) in `config.py`
- [x] Pin `spotdl>=4.4.2` in `requirements.txt` and enforce Python 3.10–3.13
  - AC: App installs with pinned spotDL; CI/check warns on Python <3.10

## Phase 1 — Config & Settings
- [x] Centralize SpotDL settings mapping in one place
  - Defaults in `config.py`; override via `.env`; allow per-request overrides
  - Map: `SPOTDL_AUDIO_SOURCE`, `SPOTDL_FORMAT`, `SPOTDL_THREADS`, `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET`, optional `GENIUS_ACCESS_TOKEN`
  - AC: Loader unit-tested; type-validated; produces `DownloaderOptionalOptions`

## Phase 2 — SpotDL Client
- [x] Instantiate a single `Spotdl` client (reuse across requests)
- [x] Before each job, set `spotdl.downloader.settings.output` to per-item template
- [x] Enable lyrics via SpotDL providers (Genius) and hook `progress_handler`
  - AC: Concurrent downloads work; progress events available; lyrics embedded

## Phase 3 — Data Models
- [ ] Use SpotDL `Song` metadata as canonical source
- [ ] Convert `Song.json` to API DTOs and DB rows (include ISRC, explicit, popularity, track/disc, year)
  - AC: No custom ad‑hoc dicts; conversions covered by tests

## Phase 4 — Service API (Flask)
- [ ] Keep existing endpoints but drive them via the new pipeline when feature flag is enabled
- [ ] Add progress stream endpoint (SSE/WebSocket) if needed by frontend
  - AC: `POST /api/download` supports track/album/playlist/compilations; progress visible

## Phase 5 — Orchestrator & Storage
- [ ] In‑process job queue for parallel jobs; retries on SpotDL errors
- [ ] Output layout unchanged; sanitize base filename; metadata JSON saved
  - AC: Idempotent handling of duplicate links; error mapping to API responses

## Phase 6 — Migration (Non‑breaking)
- [ ] Replace subprocess use in `src/download_service.py` with SpotDL API calls
- [ ] Refactor `src/spotify_content_downloader.py` to use `search()` + `download_songs()`
- [ ] Retire Spotipy usage where redundant (SpotDL provides metadata)
  - AC: Feature flag OFF → legacy behavior; ON → SpotDL service path; parity on happy paths

## Phase 7 — Lyrics Output
- [ ] Fully switch to SpotDL lyrics providers (e.g., Genius)
- [ ] After download, export embedded lyrics to `*.txt` per track alongside audio
  - AC: A `.txt` exists for each track with lyrics; graceful when lyrics missing

## Phase 8 — Frontend (React)
- [ ] Show richer metadata (ISRC, explicit, duration, etc.)
- [ ] Display multi‑track progress for albums/playlists; error messages from backend
  - AC: Usable UX for submit → progress → results

## Phase 9 — Tests & Docs
- [ ] Unit tests for config loader, SpotDL client wrapper, and download flow (mocked)
- [ ] Route tests for `/api/download` and progress endpoint
- [ ] Update README with migration notes and examples
  - AC: Green tests on branch; docs explain configuration and overrides

## Phase 10 — Cleanup
- [ ] Remove CLI subprocess code and `lyricsgenius` dependency
- [ ] Remove Spotipy‑only metadata paths (if fully redundant)
  - AC: No references to legacy flow; release notes prepared

