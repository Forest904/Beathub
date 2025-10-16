# Android-Only Mobile Development Plan

## Overview
Build a **native Android client** alongside the existing web UI while sharing business-logic packages, using the **Expo-managed workflow**.

Development will occur in **Visual Studio Code** using a **pnpm monorepo** so that shared packages stay in sync.

**Distribution:** Local **APK** only (side-load for internal testers).  
No Google Play submission, no observability, no analytics, no performance gates, and no user-facing settings.

---

## Android Target & Project Conventions

- **Min SDK:** 23+  
- **Target SDK:** Latest stable Android
- **Package name:** `com.yourorg.yourapp` (single ID)
- **Permissions (minimal):**
  - `INTERNET` — network access
  - `FOREGROUND_SERVICE` and `WAKE_LOCK` — for playback and foreground notifications
  - Scoped storage via **Expo FileSystem** (no legacy `WRITE_EXTERNAL_STORAGE`)
- **Android-first UX:**
  - System back handling
  - Media session controls
  - Foreground playback notifications
  - Adaptive icons and Android splash screen

---

## Batch 0 — Workspace Preparation and Shared Foundations

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
    - `pnpm mobile:apk:dev` → dev APK
    - `pnpm mobile:apk:release` → release APK
  - Local install instructions via `adb install <apk>`
- [x] **Acceptance**
  - App boots in **Expo Go** or as an **APK** on Android.
  - Shared hooks and domain logic function correctly.
  - APK builds locally and installs successfully.
  - No iOS artifacts exist in repo.

---

## Batch 1 — Read-Only Catalog and Download Monitoring

- [ ] Navigation:
  - Implement **Discover**, **Releases**, **Playlists**, and **Download Queue** with `@react-navigation`
  - Ensure correct **Android back behavior**
- [ ] Lists:
  - Port web list/grid to React Native **`FlatList`** and **`SectionList`**
  - Use **`expo-image`** for caching
  - Reuse **shared view models** from `packages/shared`
- [ ] Live updates:
  - Replace web **EventSource (SSE)** with **polling-based subscription**
  - Shared polling interval: 3–5s with jitter/backoff
- [ ] UX:
  - Skeleton loaders, empty/error states, and Android-native snackbars for transient feedback
- [ ] **Acceptance**
  - Users browse catalog data and view live download queue updates
  - Smooth scroll performance across Android devices
  - Graceful degradation during network interruptions

---

## Batch 2 — Authentication and Job Control

- [ ] Auth model:
  - Token-based auth with web using cookies and mobile using headers
  - Store tokens in **SecureStore** (secret) and **AsyncStorage** (non-secret)
  - Handle token refresh via shared HTTP layer
- [ ] Screens:
  - **Login/Logout** and gated navigation for download initiation
  - No settings or preference screens
- [ ] Job actions:
  - Enable **start/cancel download** using shared service hooks
  - Apply **optimistic UI updates** and reconcile with server response
- [ ] Security hygiene:
  - Hide tokens from logs
  - Clear credentials and local cache on logout
- [ ] **Acceptance**
  - Authenticated users can start/cancel jobs
  - Session persists across app restarts
  - Mobile and web reflect consistent job states

---

## Batch 3 — Device-Dependent Capabilities (Android Only)

> No user settings screen; use fixed defaults for all configurations.

- [ ] Playback:
  - Integrate **`react-native-track-player`** (preferred) or **`expo-av`**
  - Implement **Android MediaSession** for lockscreen and Bluetooth controls
  - Add **foreground playback notification** with play/pause/skip actions
- [ ] Offline caching (optional):
  - Implement **Expo FileSystem**-based caching with scoped storage
  - Enable manual clear/download controls from Downloads screen
  - Verify cache integrity with checksum or ETag validation
- [ ] Deep links (optional):
  - Support `yourapp://track/:id` for local navigation testing
  - Omit HTTPS App Links since there is no public domain
- [ ] Simplifications:
  - **No push notifications**
  - **No user settings**
- [ ] **Acceptance**
  - Users can play tracks locally and control playback via notification or lockscreen
  - Offline caching (if enabled) functions correctly and can be manually cleared
  - Player and download logic match shared contracts

---

## Deliverables & Ops (APK Only)

- **Build Outputs**
  - Development APK → `eas build --platform android --local --profile dev-apk`
  - Release APK → `eas build --platform android --local --profile release-apk`
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
- **Audio quality:** fixed to “standard”  
- **Cache limit:** fixed (e.g., 512 MB–1 GB)  
- **Push notifications:** omitted  
- **User preferences:** not stored or exposed

---
