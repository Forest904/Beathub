import { configureApiEndpoints, endpoints, getApiBaseUrl } from '@cd-collector/shared/api';

export const API_BASE_URL = (process.env.REACT_APP_API_BASE_URL || '').replace(/\/$/, '');

if (API_BASE_URL) {
  configureApiEndpoints({ baseUrl: API_BASE_URL });
}

export { configureApiEndpoints, endpoints, getApiBaseUrl };
