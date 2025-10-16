

# Desktop Application Packaging (Windows/macOS/Linux)

## Plan
- Ship an installer-like experience for desktop users bundling backend + frontend, ensuring
  offline-friendly defaults and auto-launch in the default browser.

### Batches

Batch 0 — Environment alignment
- [ ] Create `entrypoint.py` that reads config, starts the Flask app via Waitress/Hypercorn, and
      opens browser after server boot.
- [ ] Refactor settings to allow `.env` overrides and sensible platform defaults (download path,
      ffmpeg location, cache directory).
- [ ] Add smoke tests to validate that critical CLI commands still work post-refactor.
- [ ] Acceptance: App can start with `python entrypoint.py` on Windows/macOS/Linux.

Batch 1 — Packaging pipeline
- [ ] PyInstaller spec: include `frontend/build`, templates, static assets, and mark hidden imports
      (SpotDL, Spotipy, SQLAlchemy plugins).
- [ ] Ensure bundled binaries (ffmpeg) are optional; detect presence and show actionable error if
      missing.
- [ ] Automate build via `scripts/package_desktop.py` that runs PyInstaller for each target.
- [ ] Acceptance: Build artifacts land under `dist/<platform>/` with working executables.

Batch 2 — UX polish and platform integration
- [ ] Windows: Add icon resources, product metadata, and event log friendly logging path
      (`%LOCALAPPDATA%/CD-Collector/logs`).
- [ ] macOS: Create `.app` bundle with Info.plist, hardened runtime entitlement template, and
      codesign instructions.
- [ ] Linux: Provide `.AppImage` or `.deb` recipe with desktop file and MIME types.
- [ ] Acceptance: Smoke test on clean VMs for each platform; confirm downloads complete and logs
      flush to expected directories.

Batch 3 — Installer and auto-update (stretch)
- [ ] Windows: Build NSIS/Inno Setup installer with Start Menu shortcut, uninstall script, and
      optional context menu integration.
- [ ] macOS: Generate DMG with background artwork and drag-to-Applications instructions.
- [ ] Auto-update: Evaluate Sparkle (macOS) / Squirrel.Windows / appimageupdate; document decision.
- [ ] Acceptance: Install/uninstall cycle verified; updates apply without data loss.

Batch 4 — Release management
- [ ] Versioning: Adopt semantic version tied to git tags and embed build metadata in app splash.
- [ ] QA checklist per release (functional, antivirus scan, Windows Defender SmartScreen).
- [ ] Distribute checksums (SHA256) and optional GPG signatures.
- [ ] Acceptance: Release candidate promoted to stable after QA sign-off checklist passes.

### Publication Runbook — Desktop Releases
1. Cut release branch `release/desktop-vX.Y.Z`; update `VERSION` file and changelog desktop section.
2. Run `python scripts/package_desktop.py --platform windows macos linux` inside clean CI runners.
3. Virus-scan artifacts (Windows Defender, macOS Gatekeeper notarization, ClamAV for Linux).
4. Upload installers and checksums to GitHub Releases (draft), attach upgrade notes, and request QA
   sign-off.
5. After approvals, publish GitHub Release, update website download links, and notify mailing list.
6. Monitor crash/log telemetry and roll back by withdrawing binaries if high-severity issues emerge.
