import { endpoints } from "./endpoints.js";
import { httpGet } from "./httpClient.js";
import {
  toArtistSummary,
  toPlaylistDetail,
  toPlaylistSummary,
} from "./mappers.js";
import type {
  ArtistSummary,
  DownloadProgressSnapshot,
  PaginatedPlaylists,
  PlaylistDetail,
  PlaylistSummary,
} from "./types.js";

export interface PopularArtistsParams {
  limit?: number;
  page?: number;
  market?: string;
  order_by?: "popularity" | "followers";
  order_dir?: "asc" | "desc";
}

export interface PopularArtistsResponse {
  artists: ArtistSummary[];
  pagination: Record<string, unknown>;
}

export const fetchPopularArtists = async (
  params: PopularArtistsParams = {},
): Promise<PopularArtistsResponse> => {
  const data = await httpGet<{ artists?: unknown[]; pagination?: Record<string, unknown> }>(
    endpoints.artists.popular(),
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

export interface ListPlaylistsParams {
  page?: number;
  per_page?: number;
}

export const fetchPlaylistSummaries = async (
  params: ListPlaylistsParams = {},
): Promise<PaginatedPlaylists> => {
  const data = await httpGet<{ items?: unknown[]; pagination?: Record<string, unknown> }>(
    endpoints.playlists.list(),
    { params },
  );
  const items = Array.isArray(data?.items)
    ? data.items.map((item) => toPlaylistSummary(item as Record<string, unknown>))
    : [];
  return {
    items,
    pagination: data?.pagination ?? {},
  };
};

export const fetchPlaylistDetail = async (id: number | string): Promise<PlaylistDetail> => {
  const data = await httpGet<{ playlist?: Record<string, unknown> }>(endpoints.playlists.detail(id));
  const payload = (data?.playlist ?? data) as Record<string, unknown>;
  return toPlaylistDetail(payload);
};

export const fetchDownloadProgressSnapshot = async (): Promise<DownloadProgressSnapshot | null> => {
  const data = await httpGet<DownloadProgressSnapshot | null>(endpoints.progress.snapshot(), {
    validateStatus: (status) => status === 204 || (status >= 200 && status < 300),
  });

  if (!data || (typeof data === "object" && Object.keys(data).length === 0)) {
    return null;
  }

  return data;
};

export type PlaylistSummaryList = PlaylistSummary[];
