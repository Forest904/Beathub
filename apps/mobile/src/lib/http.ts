import Constants from "expo-constants";
import { Platform } from "react-native";
import { HttpClient, setDefaultHttpClient } from "@cd-collector/shared/api";
import { secureTokenStorage } from "../storage/tokenStore";

type ExpoExtraConfig = {
  apiBaseUrl?: string | null;
};

const sanitize = (value?: string | null) => value?.trim().replace(/\/$/, "") ?? "";

const DEFAULT_BASE_URL = Platform.OS === "android" ? "http://10.0.2.2:5000" : "http://127.0.0.1:5000";

const resolveBaseUrl = (): string => {
  const candidates: (ExpoExtraConfig | undefined | null)[] = [
    Constants.expoConfig?.extra as ExpoExtraConfig | undefined,
    (Constants.manifest2 as { extra?: ExpoExtraConfig } | undefined)?.extra,
    (Constants.manifest as { extra?: ExpoExtraConfig } | undefined)?.extra,
  ];

  for (const extra of candidates) {
    const candidate = sanitize(extra?.apiBaseUrl);
    if (candidate) return candidate;
  }

  return DEFAULT_BASE_URL;
};

const baseUrl = resolveBaseUrl();

if (__DEV__) {
  // eslint-disable-next-line no-console
  console.log("[http] Using API base URL:", baseUrl);
}

const httpClient = new HttpClient({
  baseUrl,
  getAuthToken: () => secureTokenStorage.read(),
});

setDefaultHttpClient(httpClient);

export default httpClient;
