# Testing Readiness Plan — Make This Branch Main-Ready

Objective: bring the codebase to a rigorously tested state using unit tests and deterministic, isolated techniques that block regressions and support confident promotion to main.

Guiding principles
- Deterministic: no network, no real disks beyond temp dirs, no external devices; everything mocked or stubbed.
- Fast feedback: unit tests first; integration behind markers; parallel where safe.
- Depth over breadth: branch coverage for decision points; property-based tests where inputs vary.
- Quality gates: enforce coverage thresholds and mutation testing on critical paths.

How to use this plan
- Work block-by-block. Each block is small and independently valuable.
- Assign me one block at a time to implement and validate.

Block 0 — Test Infrastructure and Quality Gates
- [x] Add dev tooling: pytest, pytest-cov, pytest-xdist, pytest-randomly, pytest-mock, hypothesis, freezegun, factory_boy, responses. (requirements-dev.txt)
- [x] Add `pytest.ini`: test paths, markers (`unit`, `integration`, `slow`, `network`), warnings treatment.
- [x] Add `.coveragerc`: measure `src/` and `app.py`, branch coverage, omit tests/venv, `fail_under=85`.
- [x] Add `tox.ini` to run tests across Python 3.10–3.12 with coverage gate.
- [x] Add CI workflow to run coverage-gated tests on push/PR.
Acceptance criteria
- Implemented. CI enforces ≥ 85% coverage via `--cov-fail-under=85`.

Block 1 — Config and Settings (src/settings.py, config.py)
- [x] Unit test env precedence and defaulting for all fields, including boolean parsing and overwrite validator.
- [x] Test `build_spotdl_downloader_options` mapping without importing real spotdl types (stub `spotdl.types.options.DownloaderOptionalOptions`).
- [x] Add property-based tests for env permutations that affect providers/threads/format.
Acceptance criteria
- Implemented in `tests/test_settings_block1.py`. Tests are independent of real spotdl runtime.

Block 2 — SpotDL Client Wrapper (src/spotdl_client.py)
- Expand tests to cover: engine thread init failure path; `set_output_template`; `set_progress_callback` mapping; `clear_progress_callback`.
- Verify progress wrapper tolerates callback exceptions without breaking downloads.
- Ensure `download_songs` silences stdout/stderr (simulate with a fake downloader that prints and assert nothing escapes via `capsys`).
- Test `download_link` orchestration with stubbed `.search()` and `.download_songs()`.
Acceptance criteria
- High-confidence unit tests using module-level stubs; no real spotdl usage.

Block 3 — DTO Mapping (src/models/spotdl_mapping.py, src/models/dto.py)
- Create minimal stub for `spotdl.types.song.Song` with `.json` shape and validate `song_to_track_dto` conversions and types.
- Test `songs_to_item_dto` for single vs multi-track (track vs album), cover override behavior, and error on empty list.
- Test `trackdto_to_db_kwargs` exact field mapping.
Acceptance criteria
- 100% coverage for mapping functions; strict field assertions.

Block 4 — File and Download Helpers (src/file_manager.py, src/download_service.py)
- Test filename sanitization edge cases and directory creation with tmp paths.
- Test metadata JSON save success and error handling (simulate permissions error).
- Mock `requests.get` to test cover image download success, timeout, and generic failure; assert return paths and logging behavior.
Acceptance criteria
- No network; all branches covered; no residue on disk beyond tmp dirs.

Block 5 — Lyrics Service (src/lyrics_service.py)
- Monkeypatch minimal mutagen-like stubs to unit test branches: MP3 (ID3/USLT), MP4 (lyr atom), FLAC/OGG (Vorbis comments), and “no tags”.
- Test `export_embedded_lyrics` happy path and failure to write.
Acceptance criteria
- Full branch coverage without real audio files or mutagen I/O.

Block 6 — Database Layer (src/database/db_manager.py)
- Extend DB init tests: in-memory DB does not attempt directory creation; file-backed DB creates nested dirs.
- Test `DownloadedItem.to_dict` and basic CRUD including unique/indices behavior; cascade from `DownloadedItem` to `DownloadedTrack`.
- Validate rollback on error paths.
Acceptance criteria
- Deterministic tests with app context fixture; no file DB unless using tmp path.

Block 7 — Orchestrator (src/spotify_content_downloader.py)
- Unit test `_parse_item_type` and `_extract_spotify_id` (property-based for URL shapes).
- End-to-end unit test for `download_spotify_content` with full stubs: SpotdlClient, FileManager, LyricsService, AudioCoverDownloadService, ProgressBroker, and DB session.
- Cover branches: missing spotdl client, cover image absent, lyrics export errors, DB persist failures (ensure rollback), and final metadata JSON content.
Acceptance criteria
- No network or disk writes beyond tmp dir; DB changes visible and asserted; progress events published.

Block 8 — HTTP Routes (src/routes/*)
- Expand route tests:
  - download_routes: all 2xx/4xx/5xx paths; deletion of non-existent id; metadata endpoints with missing files.
  - progress_routes: SSE stream content-type and heartbeat via time mocking; 503 when broker missing.
  - artist_routes and album_details_routes: stub Spotipy client to cover success, empty results, and error branches.
Acceptance criteria
- Route tests deterministic; no real Spotify/SpotDL calls.

Block 9 — Job Queue (src/jobs.py)
- Test idempotent submission by link; `get`, `get_by_link`, and `wait` semantics.
- Use a stub downloader to produce: success, repeated transient failures then success (retries), and permanent failure.
- Validate that Flask app context is used when provided.
Acceptance criteria
- All code paths covered; no flakiness under `-n auto`.

Block 10 — Progress Broker (src/progress.py)
- Test publish/subscribe yields valid SSE lines; unsubscribe on GeneratorExit; heartbeat using `freezegun`/monkeypatched time.
Acceptance criteria
- Deterministic timing; no sleeps > real test time.

Block 11 — Application Wiring (app.py)
- Test `configure_logging` creates a log file and configures handlers idempotently; console logging toggle obeys `ENABLE_CONSOLE_LOGS`.
- Smoke test `create_app()` registers blueprints and initializes extensions without starting SpotDL (patch builder to raise as in existing tests).
Acceptance criteria
- No server run; no global side effects beyond tmp log dir.

Block 12 — Frontend Tests (React) [Optional but recommended]
- Add Jest/RTL tests to cover pages/components using mocked fetch:
  - Submit flow (download form) happy/error; progress panel basic render.
  - Artist search and details: list rendering and error states.
  - Metadata views (album/track listing) basic snapshot and interactions.
- Add CI step for `npm ci && npm test -- --watch=false` in `frontend/`.
Acceptance criteria
- Stable component tests; no live backend required.

Block 13 — Mutation Testing (critical paths)
- Enable `mutmut` on `src/settings.py`, `src/spotdl_client.py`, `src/models/spotdl_mapping.py`, `src/routes/download_routes.py`.
- Triage and fix surviving mutants or add focused tests.
Acceptance criteria
- No trivial survivors in critical paths; document any accepted risk.

Block 14 — Test Data and Fixtures
- Add factories (factory_boy) for `DownloadedItem`/`DownloadedTrack` and common fixtures for app+DB with ephemeral sqlite.
- Centralize stubs for SpotDL and Spotipy to avoid duplication across tests.
Acceptance criteria
- Tests DRY, expressive, and faster to write.

Block 15 — Documentation and Developer UX
- Update README with: how to run tests, markers, coverage, mutation run, and CI badges.
- Add `make test`, `make test-unit`, `make test-cov` helpers or simple scripts.
Acceptance criteria
- New contributors can run the full suite with one command.

Sequencing notes
- Start with Block 0 to establish gating, then 1–5 (foundations), then 6–11 (feature coverage), then 12–15 (optional/quality).

When you’re ready, tell me which block to implement first.
