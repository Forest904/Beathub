export const DOWNLOAD_SETTINGS_STORAGE_KEY = "download-settings:v1";
export const DATE_OF_BIRTH_STORAGE_KEY = "settings:dateOfBirth";
export const THREADS_DEFAULT = 6;

export const DEFAULT_DOWNLOAD_SETTINGS = {
  base_output_dir: "./downloads",
  threads: THREADS_DEFAULT,
  preload: true,
};

export const API_KEY_FIELDS = [
  {
    key: "spotify_client_id",
    label: "Spotify Client ID",
    helper: "Create an app in the Spotify Developer Dashboard.",
    link: "https://developer.spotify.com/dashboard",
    linkLabel: "Spotify Dashboard",
  },
  {
    key: "spotify_client_secret",
    label: "Spotify Client Secret",
    helper: "Use the app you created in the Spotify Developer Dashboard to generate a new secret.",
    link: "https://developer.spotify.com/dashboard",
    linkLabel: "Spotify Dashboard",
  },
  {
    key: "genius_access_token",
    label: "Genius Access Token",
    helper: "Generate a client access token from the Genius API clients page.",
    link: "https://genius.com/api-clients",
    linkLabel: "Genius API",
  },
];

export const createEmptyApiKeysForm = () =>
  API_KEY_FIELDS.reduce((acc, field) => ({ ...acc, [field.key]: "" }), {});

export const createDefaultApiKeysMeta = () =>
  API_KEY_FIELDS.reduce((acc, field) => ({ ...acc, [field.key]: { stored: false, preview: "" } }), {});

export const createDefaultApiKeysClearState = () =>
  API_KEY_FIELDS.reduce((acc, field) => ({ ...acc, [field.key]: false }), {});
