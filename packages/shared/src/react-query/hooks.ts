import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient, QueryKey, UseMutationOptions, UseQueryOptions } from "@tanstack/react-query";
import {
  endpoints,
  fetchArtists,
  fetchDownloadHistory,
  fetchDownloadProgressSnapshot,
  fetchPlaylistDetail,
  fetchPlaylistSummaries,
  fetchPopularArtists,
  httpDelete,
} from "../api/index.js";
import type {
  DownloadItem,
  DownloadProgressSnapshot,
  PaginatedArtists,
  PaginatedPlaylists,
  PlaylistDetail,
} from "../api/types.js";
import type { ListPlaylistsParams, PopularArtistsParams, PopularArtistsResponse } from "../api/catalog.js";
import { queryKeys } from "./keys.js";

export const useDownloadHistoryQuery = <TData = DownloadItem[]>(
  options?: Omit<UseQueryOptions<DownloadItem[], Error, TData, QueryKey>, "queryKey" | "queryFn">,
) =>
  useQuery<DownloadItem[], Error, TData, QueryKey>({
    queryKey: queryKeys.downloads.history(),
    queryFn: () => fetchDownloadHistory(),
    staleTime: 1000 * 30,
    ...options,
  });

export const useRemoveDownloadMutation = (
  options?: UseMutationOptions<boolean, Error, number | string>,
) => {
  const queryClient = useQueryClient();
  return useMutation<boolean, Error, number | string>({
    mutationKey: ["downloads", "remove"],
    mutationFn: async (id) => {
      const response = await httpDelete<{ success?: boolean }>(endpoints.downloads.remove(id));
      return Boolean(response?.success);
    },
    onSuccess: async (success, id, context, mutation) => {
      if (success) {
        await queryClient.invalidateQueries({ queryKey: queryKeys.downloads.history() });
      }
      options?.onSuccess?.(success, id, context, mutation);
    },
    ...options,
  });
};

export const useArtistSearchQuery = (
  params: Record<string, string | number | boolean | undefined>,
  options?: Omit<UseQueryOptions<PaginatedArtists, Error, PaginatedArtists, QueryKey>, "queryKey" | "queryFn">,
) =>
  useQuery<PaginatedArtists, Error, PaginatedArtists, QueryKey>({
    queryKey: queryKeys.artists.search(params),
    queryFn: () => fetchArtists(params),
    staleTime: 1000 * 15,
    ...options,
  });

export const usePopularArtistsQuery = <TData = PopularArtistsResponse>(
  params: PopularArtistsParams = {},
  options?: Omit<UseQueryOptions<PopularArtistsResponse, Error, TData, QueryKey>, "queryKey" | "queryFn">,
) => {
  const hash = useMemo(() => JSON.stringify(params ?? {}), [params]);

  return useQuery<PopularArtistsResponse, Error, TData, QueryKey>({
    queryKey: queryKeys.artists.popular({ hash }),
    queryFn: () => fetchPopularArtists(params),
    staleTime: 1000 * 60,
    ...options,
  });
};

export const usePlaylistSummariesQuery = <TData = PaginatedPlaylists>(
  params: ListPlaylistsParams = {},
  options?: Omit<UseQueryOptions<PaginatedPlaylists, Error, TData, QueryKey>, "queryKey" | "queryFn">,
) => {
  const hash = useMemo(() => JSON.stringify(params ?? {}), [params]);

  return useQuery<PaginatedPlaylists, Error, TData, QueryKey>({
    queryKey: queryKeys.playlists.list({ hash }),
    queryFn: () => fetchPlaylistSummaries(params),
    staleTime: 1000 * 60,
    ...options,
  });
};

export const usePlaylistDetailQuery = <TData = PlaylistDetail>(
  id: number | string | null | undefined,
  options?: Omit<UseQueryOptions<PlaylistDetail, Error, TData, QueryKey>, "queryKey" | "queryFn">,
) => {
  const resolvedId = id;

  return useQuery<PlaylistDetail, Error, TData, QueryKey>({
    queryKey: queryKeys.playlists.detail(resolvedId ?? "unknown"),
    queryFn: () => {
      if (resolvedId === null || resolvedId === undefined) {
        throw new Error("playlist id is required");
      }
      return fetchPlaylistDetail(resolvedId);
    },
    staleTime: 1000 * 30,
    ...(options ?? {}),
    enabled: Boolean(resolvedId) && (options?.enabled ?? true),
  });
};

export interface DownloadProgressQueryOptions<TData>
  extends Omit<UseQueryOptions<DownloadProgressSnapshot | null, Error, TData, QueryKey>, "queryKey" | "queryFn"> {
  refetchIntervalMs?: number;
  jitterRatio?: number;
}

export const useDownloadProgressSnapshotQuery = <TData = DownloadProgressSnapshot | null>(
  options?: DownloadProgressQueryOptions<TData>,
) => {
  const { refetchIntervalMs = 5000, jitterRatio = 0.2, ...rest } = options ?? {};
  const {
    refetchInterval: providedInterval,
    refetchIntervalInBackground = true,
    staleTime,
    ...queryOptions
  } = rest;

  return useQuery<DownloadProgressSnapshot | null, Error, TData, QueryKey>({
    queryKey: queryKeys.downloads.progress(),
    queryFn: fetchDownloadProgressSnapshot,
    refetchInterval:
      providedInterval !== undefined
        ? providedInterval
        : () => {
            const jitter = refetchIntervalMs * jitterRatio * (Math.random() - 0.5) * 2;
            return Math.max(1500, Math.round(refetchIntervalMs + jitter));
          },
    refetchIntervalInBackground,
    staleTime: staleTime ?? Math.max(1000, Math.round(refetchIntervalMs * 0.9)),
    ...queryOptions,
  });
};
