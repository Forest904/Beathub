// Centralized API endpoints and typed DTO contracts for backend communication.
export const API_BASE_URL = process.env.REACT_APP_API_BASE_URL?.replace(/\/$/, '') || '';

export const endpoints = {
  auth: {
    session: () => `${API_BASE_URL}/api/auth/session`,
    login: () => `${API_BASE_URL}/api/auth/login`,
    logout: () => `${API_BASE_URL}/api/auth/logout`,
    register: () => `${API_BASE_URL}/api/auth/register`,
    profile: () => `${API_BASE_URL}/api/auth/profile`,
    changeEmail: () => `${API_BASE_URL}/api/auth/change-email`,
    changePassword: () => `${API_BASE_URL}/api/auth/change-password`,
  },
  downloads: {
    list: () => `${API_BASE_URL}/api/albums`,
    remove: (id) => `${API_BASE_URL}/api/albums/${id}`,
    start: () => `${API_BASE_URL}/api/download`,
    cancel: () => `${API_BASE_URL}/api/download/cancel`,
    job: (id) => `${API_BASE_URL}/api/download/jobs/${id}`,
  },
  artists: {
    search: () => `${API_BASE_URL}/api/search_artists`,
    popular: () => `${API_BASE_URL}/api/famous_artists`,
    details: (id) => `${API_BASE_URL}/api/artist_details/${id}`,
    discography: (id) => `${API_BASE_URL}/api/artist_discography/${id}`,
  },
  albums: {
    details: (id) => `${API_BASE_URL}/api/album_details/${id}`,
  },
  items: {
    metadata: (id) => `${API_BASE_URL}/api/items/${id}/metadata`,
    audio: (id, params) => {
      const query = params ? `?${new URLSearchParams(params).toString()}` : '';
      return `${API_BASE_URL}/api/items/${id}/audio${query}`;
    },
    lyrics: (id) => `${API_BASE_URL}/api/items/${id}/lyrics`,
  },
  compilations: {
    download: () => `${API_BASE_URL}/api/compilations/download`,
  },
  burner: {
    status: () => `${API_BASE_URL}/api/cd-burner/status`,
    burn: () => `${API_BASE_URL}/api/cd-burner/burn`,
    preview: () => `${API_BASE_URL}/api/cd-burner/preview`,
    devices: () => `${API_BASE_URL}/api/cd-burner/devices`,
    cancel: () => `${API_BASE_URL}/api/cd-burner/cancel`,
    selectDevice: () => `${API_BASE_URL}/api/cd-burner/select-device`,
  },
  config: {
    frontend: () => `${API_BASE_URL}/api/config/frontend`,
  },
  settings: {
    download: () => `${API_BASE_URL}/api/settings/download`,
    status: () => `${API_BASE_URL}/api/settings/status`,
  },
  playlists: {
    list: () => `${API_BASE_URL}/api/playlists`,
    detail: (id) => `${API_BASE_URL}/api/playlists/${id}`,
    tracks: (id) => `${API_BASE_URL}/api/playlists/${id}/tracks`,
    reorder: (id) => `${API_BASE_URL}/api/playlists/${id}/tracks/reorder`,
  },
  favorites: {
    list: () => `${API_BASE_URL}/api/favorites`,
    summary: () => `${API_BASE_URL}/api/favorites/summary`,
    status: () => `${API_BASE_URL}/api/favorites/status`,
    toggle: () => `${API_BASE_URL}/api/favorites/toggle`,
    remove: (id) => `${API_BASE_URL}/api/favorites/${id}`,
  },
  progressStream: () => `${API_BASE_URL}/api/progress/stream`,
};

