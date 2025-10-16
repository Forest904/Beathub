import { HttpClient, httpDelete as del, httpGet as get, httpPost as post, httpPut as put, setDefaultHttpClient } from '@cd-collector/shared/api';
import { API_BASE_URL } from './client';

const http = new HttpClient({
  baseUrl: API_BASE_URL || undefined,
});

setDefaultHttpClient(http);

export { http, get, post, del, put };
