# Android-Only Mobile Development Plan

## Overview
Build a **native Android client** alongside the existing web UI while sharing business-logic packages, using the **Expo-managed workflow**.

Development will occur in **Visual Studio Code** using a **pnpm monorepo** so that shared packages stay in sync.

**Distribution:** Local **APK** only (side-load for internal testers).  
No Google Play submission, no observability, no analytics, no performance gates, and no user-facing settings.

**Networking default:** Mobile development targets the Flask API using Expo env overrides:
- `EXPO_PUBLIC_EMULATOR_API_BASE_URL` (default `http://10.0.2.2:5000`)
- `EXPO_PUBLIC_DEVICE_API_BASE_URL` (set to your workstation LAN IP, e.g. `http://192.168.1.36:5000`)
- Optional `EXPO_PUBLIC_API_BASE_URL` if both targets should use the same host.
Metro must be restarted after changing these values.

---

## Android Target & Project Conventions

- **Min SDK:** 23+  
- **Target SDK:** Latest stable Android
- **Package name:** `com.yourorg.yourapp` (single ID)
- **Permissions (minimal):**
  - `INTERNET` - network access
  - `FOREGROUND_SERVICE` and `WAKE_LOCK` - for playback and foreground notifications
  - Scoped storage via **Expo FileSystem** (no legacy `WRITE_EXTERNAL_STORAGE`)
- **Android-first UX:**
  - System back handling
  - Media session controls
  - Foreground playback notifications
  - Adaptive icons and Android splash screen

---

## Batch 0 - Workspace Preparation and Shared Foundations

- [x] Convert repo to a **pnpm workspace** hosting:
  - `web/`
  - `apps/mobile` (workspace alias for mobile client)
  - `packages/shared`
- [x] Hoist **TypeScript**, **ESLint**, and **Prettier** configs for reuse.
- [x] Extract **API client**, **React Query** hooks, and **domain mappers** into `packages/shared` with platform-neutral interfaces:
  - HTTP wrapper with auth header injection
  - Storage abstraction for web (localStorage/IndexedDB) and mobile (SecureStore/AsyncStorage)
  - Eventing abstraction for server updates (polling-first)
- [x] Scaffold **Expo app** in `apps/mobile` for **Android** only:
  - `app.config.ts`: set `android.package`, splash, adaptive icon, optional deep link intent filters
  - `eas.json`: local build profiles for APK output (`dev-apk`, `release-apk`)
  - Styling via **`nativewind`**, aligned with web tokens
- [x] Developer ergonomics:
  - VS Code workspace tasks:  
    - `pnpm dev:web`  
    - `pnpm mobile:start`  
    - `pnpm mobile:android`
  - Scripts:
    - `pnpm mobile:apk:dev` -> dev APK
    - `pnpm mobile:apk:release` -> release APK
  - Local install instructions via `adb install <apk>`
- [x] **Acceptance**
  - App boots in **Expo Go** or as an **APK** on Android.
  - Shared hooks and domain logic function correctly.
  - APK builds locally and installs successfully.
  - No iOS artifacts exist in repo.

---

## Batch 1 - Read-Only Catalog and Download Monitoring

### Goals
Deliver a navigation shell and read-only media catalog so internal testers can browse content and monitor download progress backed by the existing services.

### Scope

- [X] Navigation
  - Add `@react-navigation/native`, `@react-navigation/native-stack`, `@react-navigation/bottom-tabs`, `react-native-screens`, and `react-native-safe-area-context` under `apps/mobile`.
  - Create `apps/mobile/src/navigation/index.tsx` exporting a root stack hosting a bottom tab navigator with screens for Discover, Releases, Playlists, and Download Queue.
  - Wire the navigation container into `App.tsx`, enable the Android back handler helpers, and confirm nested stacks respect hardware back.
  - Configure deep link prefixes for `yourapp://` so future auth work can share the same root navigator.
- [X] Lists and Detail Views
  - Port the web catalog list and grid patterns into reusable components (`CatalogList`, `CatalogGrid`) using `FlatList` and `SectionList` as appropriate.
  - Render artwork through `expo-image` with memory and disk caching enabled plus placeholder fallbacks from the design tokens.
  - Source data via shared hooks such as `useDiscoverCatalog`, `useReleaseGroups`, `usePlaylistSummaries`, and `useDownloadQueue`; keep screen components thin and push mapping logic into `packages/shared`.
  - Provide read-only release and playlist detail screens to validate navigation flows even without interactive controls.
- [X] Live Updates
  - Swap the web SSE transport for a polling abstraction (`usePollingResource`) exposed from `packages/shared`, returning cached data compatible with React Query.
  - Default interval to 3-5 seconds with +/- 750 ms jitter; pause polling when the app is backgrounded by listening to `AppState`.
  - Ensure download queue updates hydrate the shared cache so every screen stays in sync.
- [X] UX Polish
  - Add skeleton loaders (e.g. `moti/skeleton` or lightweight shimmer) and empty/error placeholders that reuse shared copy and icons.
  - Surface transient errors via a snackbar component (either `react-native-paper` or a minimal custom one) that hooks into the shared toast bus.
  - Profile low-end Android devices through the Expo dev menu; memoize list rows and provide stable `keyExtractor` values to protect scrolling performance.
- [X] Acceptance
  - Navigating among Discover, Releases, Playlists, and Download Queue behaves correctly with Android back navigation.
  - Catalog and download data render quickly, recover from offline states, and reflect server updates within five seconds under normal conditions.
  - No auth or mutation logic ships yet; all screens remain read-only while exercising the shared contracts.



---

## Batch 2 - Authentication and Job Control

### Goals
- Enforce authenticated access before users can initiate or manage download jobs.
- Share the core auth lifecycle (login, refresh, logout) with the web client while respecting platform storage constraints.
- Deliver start/cancel controls that feel instant on mobile and stay consistent with the web UI.

### Scope

- [ ] **Auth model**
  - Extend the shared HTTP client to attach auth headers, retry on 401 with refresh, and broadcast logout on irrecoverable failures.
  - Implement a cross-platform credential vault that stores refresh/secret values in SecureStore and non-secret metadata in AsyncStorage.
  - Add bootstrap logic that rehydrates sessions on cold start and blocks navigation until auth state is resolved.
- [ ] **Screens & flows**
  - Build a dedicated login stack (email/password for now) with inline error states and submit throttling; redirect authenticated users back to the main tab navigator.
  - Surface a logout affordance in the Downloads tab header overflow and apply a confirmation step before clearing data.
  - Gate job controls behind auth-aware guards so guests see a prompt to log in instead of actionable buttons.
- [ ] **Job actions**
  - Wire startDownload and cancelDownload mutations from packages/shared with optimistic cache updates and eventual reconciliation from polling responses.
  - Provide inline progress indicators and status toasts for success/failure, rolling back optimistic state if the server rejects the change.
  - Ensure the mobile queue remains in sync with concurrent actions triggered from the web client or background jobs.
- [ ] **Security hygiene**
  - Redact token material from logs, analytics events, and crash reports.
  - On logout, purge cached queries, reset mutation queues, clear persisted storage, and wipe any temporary download artifacts tied to the session.
  - Guard against stale refresh tokens by checking expiry timestamps and forcing relogin when refresh fails.

### Acceptance
- Authenticated users can start and cancel download jobs on mobile with state reflected in subsequent refreshes.
- Session state survives app restarts and surfaces an inline login when credentials expire.
- Mobile and web maintain consistent job state after concurrent actions, including rollback on error.
- Logging out removes all sensitive data and returns the app to a guest-safe navigation state.

---

## Batch 3 - Device-Dependent Capabilities (Android Only)

### Goals
- Deliver reliable Android playback integrated with system surfaces even without iOS parity.
- Provide offline access and deep link affordances where they create concrete value for testers.
- Keep the scope tight by omitting push notifications and end-user preferences.

### Scope

- [ ] **Playback**
  - Integrate `expo-av` as the definitive playback engine, configuring background audio, notification channel, and lifecycle hooks within the managed workflow.
  - Configure Android MediaSession with lockscreen, notification, and Bluetooth transport controls mapped to shared playback commands.
  - Present a foreground playback notification with play/pause/skip actions plus artwork synced to the active track.
  - Handle audio focus changes and noisy events (for example, headphones unplugged) to pause gracefully.
- [ ] **Offline caching (optional)**
  - Use Expo FileSystem with scoped storage to persist downloaded audio and related metadata.
  - Track disk usage, enforce a fixed cache cap (512 MB-1 GB), and expose a manual clear/download management affordance within the Downloads tab.
  - Validate file integrity via checksum or ETag comparison before marking a download complete.
- [ ] **Deep links (optional)**
  - Support `yourapp://track/:id` to jump into playback or detail views; ensure links authenticate before navigation.
  - Register intent filters in `app.config.ts` while skipping HTTPS App Links since there is no public domain.
- [ ] **Simplifications**
  - No push notifications.
  - No user-facing playback or cache settings; rely on fixed defaults from shared config.

### Acceptance
- Users can play tracks locally, control playback from the notification tray or lockscreen, and observe responsive Bluetooth controls.
- Offline caching (when enabled) stores tracks, survives app restarts, and can be cleared through the Downloads tab without leftover files.
- Deep links (when enabled) navigate correctly and respect auth guards.
- Playback and download state remain aligned with shared domain expectations under error and background conditions.

---

## Deliverables & Ops (APK Only)

- **Build Outputs**
  - Development APK -> `eas build --platform android --local --profile dev-apk`
  - Release APK -> `eas build --platform android --local --profile release-apk`
- **Signing**
  - Use **debug keystore** or locally generated release keystore (`keytool`)
  - No Play Console signing required
- **Distribution**
  - Side-load via ADB:  
    `adb install -r path/to/app.apk`
  - Share APK internally through a CI artifact or file share
- **CI (optional)**
  - Run lint, typecheck, and tests on PRs
  - Produce release APK artifacts on main or tagged branches
- **Documentation**
  - `README-mobile.md` including:
    - Setup
    - Local run instructions (`pnpm i && pnpm mobile:start`)
    - Build/install walkthrough
  - Troubleshooting section for emulator/device issues

---

## Defaults & Assumptions

Since there are **no user settings**:

- **Theme:** follows system light/dark mode  
- **Audio quality:** fixed to "standard"  
- **Cache limit:** fixed (e.g., 512 MB-1 GB)  
- **Push notifications:** omitted  
- **User preferences:** not stored or exposed

---
