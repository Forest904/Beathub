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
- Implemented in `tests/unit/settings/test_settings.py`. Tests are independent of real spotdl runtime.

Block 2 — SpotDL Client Wrapper (src/spotdl_client.py)
- [x] Expand tests to cover: engine thread init failure path; `set_output_template`; `set_progress_callback` mapping; `clear_progress_callback`.
- [x] Verify progress wrapper tolerates callback exceptions without breaking downloads.
- [x] Ensure `download_songs` silences stdout/stderr (simulate prints and assert nothing escapes via `capsys`).
- [x] Test `download_link` orchestration with stubbed `.search()` and `.download_songs()`.
Acceptance criteria
- Implemented in `tests/unit/clients/test_spotdl_client_behaviour.py`; uses stubs only, no real spotdl.

Block 3 — DTO Mapping (src/models/spotdl_mapping.py, src/models/dto.py)
- [x] Create minimal stub for `spotdl.types.song.Song` with `.json` shape and validate `song_to_track_dto` conversions and types.
- [x] Test `songs_to_item_dto` for single vs multi-track (track vs album), cover override behavior, and error on empty list.
- [x] Test `trackdto_to_db_kwargs` exact field mapping.
Acceptance criteria
- Implemented in `tests/unit/models/test_spotdl_mapping.py` with strict assertions.

Block 4 — File and Download Helpers (src/file_manager.py, src/download_service.py)
- [x] Test filename sanitization edge cases and directory creation with tmp paths.
- [x] Test metadata JSON save success and error handling (simulate write error).
- [x] Mock `requests.get` to test cover image download success, timeout, generic failure, and write error; assert outputs.
Acceptance criteria
- Implemented in `tests/unit/downloads/test_file_manager.py` and `tests/unit/downloads/test_download_service.py` with no network and tmp-only I/O.

Block 5 — Lyrics Service (src/lyrics_service.py)
- [x] Monkeypatch minimal mutagen-like stubs to unit test branches: MP3 (ID3/USLT), MP4 (lyr atom), FLAC/OGG (Vorbis comments), and missing file handling.
- [x] Test `export_embedded_lyrics` happy path and failure to write.
Acceptance criteria
- Implemented in `tests/unit/lyrics/test_lyrics_service.py` without real mutagen or audio files.

Block 6 — Database Layer (src/database/db_manager.py)
- [x] Extend DB init tests: in-memory DB does not attempt directory creation; file-backed DB covered in existing tests.
- [x] Test `DownloadedItem.to_dict` and basic CRUD with unique constraint on `spotify_id`; session rollback and reuse.
- [x] Validate relationship link between `DownloadedItem` and `DownloadedTrack` via `item_id` and backref.
Acceptance criteria
- Implemented in `tests/unit/database/test_db_manager.py` using app context and tmp paths only.

Block 7 — Orchestrator (src/spotify_content_downloader.py)
- [x] Unit test `_parse_item_type` and `_extract_spotify_id`.
- [x] End-to-end unit test for `download_spotify_content` with full stubs for SpotDL client and services.
- [x] Cover branches: missing spotdl client, cover image absent, lyrics export errors, DB commit failure with rollback; verify metadata JSON and progress events.
Acceptance criteria
- Implemented in `tests/unit/orchestrator/test_spotify_content_downloader.py`; no network; tmp-only I/O; DB assertions included.

Block 8 — HTTP Routes (src/routes/*)
- [x] download_routes: success/400/500 paths; deletion of non-existent id; metadata endpoints with missing files.
- [x] progress_routes: SSE stream content-type and heartbeat; 503 when broker missing (covered earlier).
- [x] artist_routes and album_details_routes: stub Spotipy/metadata service covering success, empty, and error branches.
Acceptance criteria
- Implemented in `tests/unit/routes/test_routes_api.py` (complements existing `tests/unit/routes/test_routes_general.py`). Deterministic; no real external calls.

Block 9 — Job Queue (src/jobs.py)
- [x] Test idempotent submission by link; `get`, `get_by_link`, and `wait` semantics.
- [x] Stub downloader flows: immediate success; transient failures then success (retries); permanent failure.
- [x] Validate worker executes within Flask app context when provided.
Acceptance criteria
- Implemented in `tests/unit/jobs/test_jobs.py`; deterministic and fast.

Block 10 — Progress Broker (src/progress.py)
- [x] Test publish/subscribe yields valid SSE lines from events.
- [x] Test heartbeat emission using monkeypatched time and non-blocking queue.get.
- [x] Test unsubscribe (GeneratorClose) removes subscriber.
Acceptance criteria
- Implemented in `tests/unit/progress/test_progress.py` with deterministic timing and no real sleeps.

Block 11 — Application Wiring (app.py)
- [x] Test `configure_logging` creates a log file and stays idempotent; console logging toggle obeys `ENABLE_CONSOLE_LOGS`.
- [x] Smoke test `create_app()` registers blueprints and core extensions without starting SpotDL.
Acceptance criteria
- Implemented in `tests/unit/app/test_app.py`; no server run; logging state restored after tests.

Block 12 — Test Data and Fixtures
- Add factories (factory_boy) for `DownloadedItem`/`DownloadedTrack` and common fixtures for app+DB with ephemeral sqlite.
- Centralize stubs for SpotDL and Spotipy to avoid duplication across tests.
Acceptance criteria
- Tests DRY, expressive, and faster to write.

Block 13 — Documentation and Developer UX
- Update README with: how to run tests, markers, coverage, mutation run, and CI badges.
- Add `make test`, `make test-unit`, `make test-cov` helpers or simple scripts.
Acceptance criteria
- New contributors can run the full suite with one command.

Sequencing notes
- Start with Block 0 to establish gating, then 1–5 (foundations), then 6–11 (feature coverage), then 12–15 (optional/quality).

When you’re ready, tell me which block to implement first.
