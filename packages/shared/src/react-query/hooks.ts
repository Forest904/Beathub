import { useMutation, useQuery, useQueryClient, QueryKey, UseMutationOptions, UseQueryOptions } from "@tanstack/react-query";
import { endpoints, fetchArtists, fetchDownloadHistory, httpDelete } from "../api/index.js";
import type { DownloadItem, PaginatedArtists } from "../api/types.js";
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
