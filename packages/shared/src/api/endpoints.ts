export interface ApiEndpointsConfig {
  baseUrl?: string;
}

let apiBaseUrl = "";

export const configureApiEndpoints = (config: ApiEndpointsConfig = {}) => {
  apiBaseUrl = (config.baseUrl ?? "").replace(/\/$/, "");
};

const withBase = (path: string) => {
  if (!apiBaseUrl) return path;
  return `${apiBaseUrl}${path}`;
};

export const endpoints = {
  auth: {
    session: () => withBase("/api/auth/session"),
    login: () => withBase("/api/auth/login"),
    logout: () => withBase("/api/auth/logout"),
    register: () => withBase("/api/auth/register"),
  },
  downloads: {
    list: () => withBase("/api/albums"),
    remove: (id: number | string) => withBase(`/api/albums/${id}`),
    start: () => withBase("/api/download"),
    cancel: () => withBase("/api/download/cancel"),
    job: (id: number | string) => withBase(`/api/download/jobs/${id}`),
  },
  artists: {
    search: () => withBase("/api/search_artists"),
    popular: () => withBase("/api/famous_artists"),
    details: (id: string | number) => withBase(`/api/artist_details/${id}`),
    discography: (id: string | number) => withBase(`/api/artist_discography/${id}`),
  },
  albums: {
    details: (id: string | number) => withBase(`/api/album_details/${id}`),
  },
  items: {
    metadata: (id: string | number) => withBase(`/api/items/${id}/metadata`),
    audio: (id: string | number, params?: Record<string, string | number | boolean | undefined>) => {
      const searchParams = new URLSearchParams();
      if (params) {
        Object.entries(params).forEach(([key, value]) => {
          if (value === undefined || value === null) return;
          searchParams.append(key, String(value));
        });
      }
      const query = searchParams.toString();
      return `${withBase(`/api/items/${id}/audio`)}${query ? `?${query}` : ""}`;
    },
    lyrics: (id: string | number) => withBase(`/api/items/${id}/lyrics`),
  },
  compilations: {
    download: () => withBase("/api/compilations/download"),
  },
  burner: {
    status: () => withBase("/api/cd-burner/status"),
    burn: () => withBase("/api/cd-burner/burn"),
    preview: () => withBase("/api/cd-burner/preview"),
    devices: () => withBase("/api/cd-burner/devices"),
    cancel: () => withBase("/api/cd-burner/cancel"),
    selectDevice: () => withBase("/api/cd-burner/select-device"),
  },
  config: {
    frontend: () => withBase("/api/config/frontend"),
  },
  playlists: {
    list: () => withBase("/api/playlists"),
    detail: (id: string | number) => withBase(`/api/playlists/${id}`),
    tracks: (id: string | number) => withBase(`/api/playlists/${id}/tracks`),
    reorder: (id: string | number) => withBase(`/api/playlists/${id}/tracks/reorder`),
  },
  favorites: {
    list: () => withBase("/api/favorites"),
    summary: () => withBase("/api/favorites/summary"),
    status: () => withBase("/api/favorites/status"),
    toggle: () => withBase("/api/favorites/toggle"),
    remove: (id: string | number) => withBase(`/api/favorites/${id}`),
  },
  progress: {
    stream: () => withBase("/api/progress/stream"),
    snapshot: () => withBase("/api/progress/snapshot"),
  },
};

export const getApiBaseUrl = () => apiBaseUrl;
