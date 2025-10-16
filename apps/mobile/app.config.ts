import { ConfigContext, ExpoConfig } from '@expo/config';

const androidPackage = 'com.cdcollector.mobile';

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: 'CD Collector',
  slug: 'cd-collector-mobile',
  scheme: 'cdcollector',
  version: '0.1.0',
  orientation: 'portrait',
  userInterfaceStyle: 'automatic',
  platforms: ['android'],
  assetBundlePatterns: ['**/*'],
  android: {
    package: androidPackage,
    permissions: ['INTERNET', 'WAKE_LOCK', 'FOREGROUND_SERVICE'],
    adaptiveIcon: {
      foregroundImage: './assets/adaptive-icon.png',
      backgroundColor: '#0f172a',
    },
    splash: {
      image: './assets/splash.png',
      resizeMode: 'contain',
      backgroundColor: '#0f172a',
    },
    intentFilters: [
      {
        action: 'VIEW',
        data: [
          {
            scheme: 'cdcollector',
            host: 'downloads',
            pathPrefix: '/',
          },
        ],
        category: ['BROWSABLE', 'DEFAULT'],
      },
    ],
  },
  splash: {
    image: './assets/splash.png',
    resizeMode: 'contain',
    backgroundColor: '#0f172a',
  },
  extra: {
    apiBaseUrl: process.env.EXPO_PUBLIC_API_BASE_URL ?? '',
  },
});
