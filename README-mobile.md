# CD Collector Mobile (Expo)

The mobile client lives under `apps/mobile` in the pnpm workspace.

## Prerequisites

- Node.js 18+
- pnpm 9+
- Android SDK / emulator or physical device with USB debugging
- `expo` CLI (`npm i -g expo-cli`) if you prefer direct CLI access

## Installation

```bash
pnpm install
```

## Running in Development

```bash
# Start Metro with Android target
export EXPO_PUBLIC_API_BASE_URL=http://<your-computer-ip>:5000
pnpm mobile:start
```

The API URL defaults to the same origin as the Metro server. Override `EXPO_PUBLIC_API_BASE_URL` when running on a device.

## Building APKs Locally

`apps/mobile/eas.json` provides local profiles:

```bash
pnpm mobile:apk:dev
pnpm mobile:apk:release
```

Install the resulting APK using `adb install -r path/to/app.apk`.

## Shared Foundations

The Expo app consumes the `@cd-collector/shared` package for:

- HTTP client + auth token injection
- React Query hooks (`createQueryClient`, domain queries)
- Storage adapters (SecureStore / AsyncStorage)
- Polling-based progress subscriptions (`createProgressSubscription`)

`apps/mobile/src/lib/http.ts` wires the shared HTTP client to Expo configuration and SecureStore.

## Folder Layout

```
apps/mobile/
  app.config.ts       # Expo configuration (Android only)
  eas.json            # Local build profiles
  tailwind.config.js  # NativeWind + shared tokens
  src/
    App.tsx
    lib/http.ts
    storage/          # SecureStore & AsyncStorage bridges
```
