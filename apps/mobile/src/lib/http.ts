import Constants from 'expo-constants';
import { HttpClient, setDefaultHttpClient } from '@cd-collector/shared/api';
import { secureTokenStorage } from '../storage/tokenStore';

const baseUrl = (Constants?.expoConfig?.extra?.apiBaseUrl as string | undefined) ?? '';

const httpClient = new HttpClient({
  baseUrl: baseUrl || undefined,
  getAuthToken: () => secureTokenStorage.read(),
});

setDefaultHttpClient(httpClient);

export default httpClient;
