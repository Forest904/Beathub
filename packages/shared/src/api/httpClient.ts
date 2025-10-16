import axios, { AxiosInstance, AxiosRequestConfig } from "axios";
import { configureApiEndpoints } from "./endpoints.js";

export type AuthTokenProvider = () => string | null | Promise<string | null>;

export interface HttpClientConfig {
  baseUrl?: string;
  getAuthToken?: AuthTokenProvider;
  onUnauthorized?: () => void;
}

export class HttpClient {
  private instance: AxiosInstance;

  private getAuthToken?: AuthTokenProvider;

  private onUnauthorized?: () => void;

  constructor(config: HttpClientConfig = {}) {
    const { baseUrl, getAuthToken, onUnauthorized } = config;
    if (baseUrl) {
      configureApiEndpoints({ baseUrl });
    }
    this.getAuthToken = getAuthToken;
    this.onUnauthorized = onUnauthorized;

    this.instance = axios.create({
      baseURL: baseUrl,
      withCredentials: true,
    });

    this.instance.interceptors.request.use(async (request) => {
      if (!this.getAuthToken) return request;
      const token = await this.getAuthToken();
      if (token) {
        request.headers = request.headers ?? {};
        request.headers.Authorization = `Bearer ${token}`;
      }
      return request;
    });

    this.instance.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error?.response?.status === 401 && this.onUnauthorized) {
          this.onUnauthorized();
        }
        if (error?.response?.data?.errors) {
          const apiError = new Error("API validation error");
          apiError.name = "ApiValidationError";
          // @ts-expect-error augmenting typed error object
          apiError.details = error.response.data.errors;
          // @ts-expect-error augmenting typed error object
          apiError.status = error.response.status;
          throw apiError;
        }
        throw error;
      },
    );
  }

  request<T = unknown>(config: AxiosRequestConfig): Promise<T> {
    return this.instance.request<T>(config).then((response) => response.data);
  }

  get<T = unknown>(url: string, config?: AxiosRequestConfig) {
    return this.request<T>({ ...config, method: "GET", url });
  }

  post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig) {
    return this.request<T>({ ...config, method: "POST", url, data });
  }

  put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig) {
    return this.request<T>({ ...config, method: "PUT", url, data });
  }

  delete<T = unknown>(url: string, config?: AxiosRequestConfig) {
    return this.request<T>({ ...config, method: "DELETE", url });
  }
}

let defaultClient: HttpClient | null = null;

export const getDefaultHttpClient = () => {
  if (!defaultClient) {
    defaultClient = new HttpClient();
  }
  return defaultClient;
};

export const setDefaultHttpClient = (client: HttpClient) => {
  defaultClient = client;
};

export const httpGet = async <T = unknown>(url: string, config?: AxiosRequestConfig) =>
  getDefaultHttpClient().get<T>(url, config);

export const httpPost = async <T = unknown>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
) => getDefaultHttpClient().post<T>(url, data, config);

export const httpPut = async <T = unknown>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
) => getDefaultHttpClient().put<T>(url, data, config);

export const httpDelete = async <T = unknown>(url: string, config?: AxiosRequestConfig) =>
  getDefaultHttpClient().delete<T>(url, config);
