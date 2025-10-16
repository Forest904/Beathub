import { httpGet } from "./httpClient.js";
import { endpoints } from "./endpoints.js";
import type { ArtistSummary, DownloadItem, PaginatedArtists } from "./types.js";

export const toDownloadItem = (raw: Record<string, unknown>): DownloadItem => ({
  id: Number(raw?.id ?? 0),
  spotify_id: String(raw?.spotify_id ?? ""),
  name: String(raw?.title ?? raw?.name ?? ""),
  title: String(raw?.title ?? ""),
  artist: String(raw?.artist ?? ""),
  image_url: raw?.image_url ? String(raw.image_url) : null,
  spotify_url: raw?.spotify_url ? String(raw.spotify_url) : null,
  local_path: raw?.local_path ? String(raw.local_path) : null,
  is_favorite: Boolean(raw?.is_favorite),
  item_type: String(raw?.item_type ?? "unknown"),
});

export const toArtistSummary = (raw: Record<string, unknown>): ArtistSummary => ({
  id: String(raw?.id ?? ""),
  name: String(raw?.name ?? ""),
  genres: Array.isArray(raw?.genres) ? raw.genres.map(String) : [],
  followers: Number(raw?.followers ?? 0),
  popularity: Number(raw?.popularity ?? 0),
  followers_available: Boolean(raw?.followers_available),
  popularity_available: Boolean(raw?.popularity_available),
  image: raw?.image ? String(raw.image) : null,
  external_urls: (raw?.external_urls as Record<string, unknown> | null | undefined) ?? null,
});

export const fetchDownloadHistory = async (): Promise<DownloadItem[]> => {
  const data = await httpGet<unknown[]>(endpoints.downloads.list());
  if (!Array.isArray(data)) return [];
  return data.map((item) => toDownloadItem(item as Record<string, unknown>));
};

export const fetchArtists = async (
  params: Record<string, string | number | boolean | undefined>,
): Promise<PaginatedArtists> => {
  const data = await httpGet<{ artists?: unknown[]; pagination?: Partial<PaginatedArtists["pagination"]> }>(
    endpoints.artists.search(),
    { params },
  );
  const artists = Array.isArray(data?.artists)
    ? data.artists.map((item) => toArtistSummary(item as Record<string, unknown>))
    : [];
  return {
    artists,
    pagination: data?.pagination ?? {},
  };
};
