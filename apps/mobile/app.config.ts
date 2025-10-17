import { ConfigContext, ExpoConfig } from "expo/config";
import path from "node:path";
import fs from "node:fs";

const loadEnvIfPresent = (envPath: string) => {
  if (!fs.existsSync(envPath)) {
    return;
  }
  const envFile = fs.readFileSync(envPath, "utf8");
  for (const line of envFile.split(/\r?\n/)) {
    if (!line || line.startsWith("#")) continue;
    const [rawKey, ...rest] = line.split("=");
    if (!rawKey) continue;
    const key = rawKey.trim();
    if (!key.startsWith("EXPO_PUBLIC_")) continue;
    if (process.env[key] !== undefined) continue;
    const value = rest.join("=").trim();
    process.env[key] = value;
  }
};

const repoEnvPath = path.resolve(__dirname, "..", "..", ".env");
const mobileEnvPath = path.resolve(__dirname, ".env");
loadEnvIfPresent(repoEnvPath);
loadEnvIfPresent(mobileEnvPath);

const androidPackage = "com.cdcollector.mobile";

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: "CD Collector",
  slug: "cd-collector-mobile",
  scheme: "cdcollector",
  version: "0.1.0",
  orientation: "portrait",
  userInterfaceStyle: "automatic",
  platforms: ["android"],
  assetBundlePatterns: ["**/*"],
  android: {
    package: androidPackage,
    permissions: ["INTERNET", "WAKE_LOCK", "FOREGROUND_SERVICE"],
    adaptiveIcon: {
      foregroundImage: "./assets/adaptive-icon.png",
      backgroundColor: "#0f172a",
    },
    splash: {
      image: "./assets/splash.png",
      resizeMode: "contain",
      backgroundColor: "#0f172a",
    },
    intentFilters: [
      {
        action: "VIEW",
        data: [
          {
            scheme: "cdcollector",
            host: "downloads",
            pathPrefix: "/",
          },
        ],
        category: ["BROWSABLE", "DEFAULT"],
      },
    ],
  },
  splash: {
    image: "./assets/splash.png",
    resizeMode: "contain",
    backgroundColor: "#0f172a",
  },
  extra: {
    apiBaseUrl: process.env.EXPO_PUBLIC_API_BASE_URL ?? "",
    emulatorApiBaseUrl: process.env.EXPO_PUBLIC_EMULATOR_API_BASE_URL ?? "http://10.0.2.2:5000",
    deviceApiBaseUrl: process.env.EXPO_PUBLIC_DEVICE_API_BASE_URL ?? "",
  },
});
