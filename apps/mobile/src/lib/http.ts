import Constants from "expo-constants";
import { HttpClient, setDefaultHttpClient } from "@cd-collector/shared/api";
import { secureTokenStorage } from "../storage/tokenStore";

type ExpoExtraConfig = {
  apiBaseUrl?: string | null;
  emulatorApiBaseUrl?: string | null;
  deviceApiBaseUrl?: string | null;
};

const sanitize = (value?: string | null) => value?.trim().replace(/\/$/, "") ?? "";

const DEFAULT_BASE_URL = "http://10.0.2.2:5000";
const extraSources: (ExpoExtraConfig | undefined)[] = [
  Constants.expoConfig?.extra as ExpoExtraConfig | undefined,
  (Constants.manifest2 as { extra?: ExpoExtraConfig } | undefined)?.extra,
  (Constants.manifest as { extra?: ExpoExtraConfig } | undefined)?.extra,
];

const resolveBaseUrl = (): { url: string; source: "device" | "emulator" | "fallback" | "default" } => {
  const merged: ExpoExtraConfig = {};
  for (const extra of extraSources) {
    if (!extra) continue;
    merged.apiBaseUrl ??= extra.apiBaseUrl;
    merged.emulatorApiBaseUrl ??= extra.emulatorApiBaseUrl;
    merged.deviceApiBaseUrl ??= extra.deviceApiBaseUrl;
  }

  const apiBaseUrl = sanitize(merged.apiBaseUrl);
  const emulatorBaseUrl = sanitize(merged.emulatorApiBaseUrl);
  const deviceBaseUrl = sanitize(merged.deviceApiBaseUrl);

  if (Constants.isDevice && deviceBaseUrl) {
    return { url: deviceBaseUrl, source: "device" };
  }

  if (!Constants.isDevice && emulatorBaseUrl) {
    return { url: emulatorBaseUrl, source: "emulator" };
  }

  if (apiBaseUrl) {
    return { url: apiBaseUrl, source: "fallback" };
  }

  return { url: DEFAULT_BASE_URL, source: "default" };
};

const { url: baseUrl, source } = resolveBaseUrl();

const sourceLabel: Record<typeof source, string> = {
  device: "Expo device override",
  emulator: "Expo emulator override",
  fallback: "Expo base URL override",
  default: "Expo default",
};

// eslint-disable-next-line no-console
console.log(`[http] Using API base URL: ${baseUrl} (${sourceLabel[source]})`);

const httpClient = new HttpClient({
  baseUrl,
  getAuthToken: () => secureTokenStorage.read(),
});

setDefaultHttpClient(httpClient);

export default httpClient;
