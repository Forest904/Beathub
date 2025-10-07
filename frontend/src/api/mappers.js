import { endpoints } from './client';
import { get } from './http';

export const fetchDownloadHistory = async () => {
  const data = await get(endpoints.downloads.list());
  return Array.isArray(data) ? data.map(toDownloadItem) : [];
};

/**
 * @param {any} raw
 * @returns {import('./types').DownloadItem}
 */
export const toDownloadItem = (raw) => ({
  id: Number(raw?.id ?? 0),
  spotify_id: String(raw?.spotify_id ?? ''),
  title: String(raw?.title ?? ''),
  artist: String(raw?.artist ?? ''),
  image_url: raw?.image_url ?? null,
  spotify_url: raw?.spotify_url ?? null,
  local_path: raw?.local_path ?? null,
  is_favorite: Boolean(raw?.is_favorite),
  item_type: String(raw?.item_type ?? 'unknown'),
});

/**
 * @param {any} raw
 * @returns {import('./types').ArtistSummary}
 */
export const toArtistSummary = (raw) => ({
  id: String(raw?.id ?? ''),
  name: String(raw?.name ?? ''),
  genres: Array.isArray(raw?.genres) ? raw.genres.map(String) : [],
  followers: Number(raw?.followers ?? 0),
  popularity: Number(raw?.popularity ?? 0),
  followers_available: Boolean(raw?.followers_available),
  popularity_available: Boolean(raw?.popularity_available),
  image: raw?.image ?? null,
  external_urls: raw?.external_urls ?? null,
});

export const fetchArtists = async (params) => {
  const data = await get(endpoints.artists.search(), { params });
  const { artists = [], pagination = {} } = data || {};
  return {
    artists: Array.isArray(artists) ? artists.map(toArtistSummary) : [],
    pagination,
  };
};
