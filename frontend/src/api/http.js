import axios from 'axios';
import { API_BASE_URL } from './client';

export const http = axios.create({
  baseURL: API_BASE_URL || undefined,
  withCredentials: true,
});

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.data?.errors) {
      throw Object.assign(new Error('API validation error'), {
        name: 'ApiValidationError',
        details: error.response.data.errors,
        status: error.response.status,
      });
    }
    throw error;
  },
);

export const get = (url, config) => http.get(url, config).then((resp) => resp.data);
export const post = (url, body, config) => http.post(url, body, config).then((resp) => resp.data);
export const del = (url, config) => http.delete(url, config).then((resp) => resp.data);
export const put = (url, body, config) => http.put(url, body, config).then((resp) => resp.data);
export const patch = (url, body, config) => http.patch(url, body, config).then((resp) => resp.data);
