## Mobile Application (React Native / Expo)

### Plan
- Build a native mobile client alongside the existing web UI while sharing business logic packages,
  targeting iOS and Android through the Expo-managed workflow. Development will happen in
  Visual Studio Code using the monorepo workspace so that shared packages stay in sync.

### Batches

Batch 0 — Workspace preparation and shared foundations
- [ ] Convert repo to a pnpm workspace hosting `web/`, `mobile/`, and `packages/shared` with linting
      and TypeScript config hoisted for reuse.
- [ ] Extract API client, React Query hooks, and domain mappers into `packages/shared` with
      platform-neutral abstractions for HTTP, storage, and streaming.
- [ ] Scaffold Expo app (`apps/mobile`) configured for EAS builds, Tailwind tokens via `nativewind`,
      and linting/prettier aligned with the web project.
- [ ] Acceptance: Mobile app boots in Expo Go, consumes shared hooks for catalog queries, and VS Code
      workspace tasks run the correct bundle commands.

Batch 1 — Read-only catalog and download monitoring
- [ ] Implement navigation stacks/tabs mirroring Discover, Releases, Playlists, and Download Queue
      screens with read-only data.
- [ ] Adapt list/grid components to React Native FlatList/SectionList while keeping shared view models.
- [ ] Replace EventSource usage with a shared polling/subscription abstraction that supports Expo
      (fallback to polling until native SSE is validated).
- [ ] Acceptance: Users can browse catalog data and see live download status updates without issuing
      new jobs.

Batch 2 — Authentication and job control
- [ ] Introduce token-based authentication flow compatible with both cookie (web) and header
      (mobile) strategies; persist mobile tokens via SecureStore wrapper in shared auth provider.
- [ ] Add login/logout screens, account context, and gated navigation for download initiation.
- [ ] Enable job submission/cancellation by adapting existing download service hooks to mobile UI
      actions, ensuring optimistic UI matches web behavior.
- [ ] Acceptance: Authenticated users start/cancel jobs from mobile and see state reflected on web.

Batch 3 — Device-dependent capabilities
- [ ] Integrate `expo-av` (or `react-native-track-player`) behind the shared player context to deliver
      local playback controls identical to the web API.
- [ ] Implement optional offline caching via Expo FileSystem, including quota management and manual
      clear/download controls.
- [ ] Add user settings for audio quality, cache size, and theme synced via shared settings provider
      (wrapping Expo SecureStore/AsyncStorage adapters).
- [ ] Acceptance: Mobile users can play tracks locally, manage stored files, and adjust preferences
      without breaking shared logic contracts.
