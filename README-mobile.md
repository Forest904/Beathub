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
pnpm mobile:start
```

Networking defaults are controlled via Expo public env vars (see `.env`):

- `EXPO_PUBLIC_EMULATOR_API_BASE_URL` -> used when running on an emulator (defaults to `http://10.0.2.2:5000`)
- `EXPO_PUBLIC_DEVICE_API_BASE_URL` -> used on a physical device (set this to your host machine’s LAN IP, e.g. `http://192.168.1.36:5000`)
- `EXPO_PUBLIC_API_BASE_URL` -> optional shared override if you want both targets to hit the same backend

Restart Metro after editing these values so Expo picks up the changes.

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
