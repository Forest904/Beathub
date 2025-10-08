import { useMemo } from 'react';
import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';

import {
  addTracksToPlaylist,
  createPlaylist as createPlaylistApi,
  deletePlaylist as deletePlaylistApi,
  fetchPlaylist,
  fetchPlaylists,
  removeTrackFromPlaylist,
  reorderPlaylistTracks,
  updatePlaylist as updatePlaylistApi,
} from '../api';
import { useAuth } from '../../../shared/hooks/useAuth';

export const PLAYLIST_DEFAULT_PAGE_SIZE = 10;

export const playlistKeys = {
  all: ['playlists'],
  listPrefix: ['playlists', 'list'],
  list: (page = 1, perPage = PLAYLIST_DEFAULT_PAGE_SIZE) => [
    'playlists',
    'list',
    page,
    perPage,
  ],
  detailPrefix: ['playlists', 'detail'],
  detail: (id) => ['playlists', 'detail', id],
};

const nowIso = () => new Date().toISOString();

export const usePlaylistList = ({
  page = 1,
  perPage = PLAYLIST_DEFAULT_PAGE_SIZE,
} = {}) => {
  const { user } = useAuth();
  return useQuery({
    queryKey: playlistKeys.list(page, perPage),
    queryFn: () => fetchPlaylists({ page, per_page: perPage }),
    enabled: Boolean(user),
    keepPreviousData: true,
    staleTime: 1000 * 30,
  });
};

export const usePlaylist = (playlistId) => {
  const { user } = useAuth();
  return useQuery({
    queryKey: playlistKeys.detail(playlistId),
    queryFn: () => fetchPlaylist(playlistId).then((response) => response.playlist),
    enabled: Boolean(user && playlistId),
    staleTime: 1000 * 30,
  });
};

const applyToListCaches = (queryClient, updater) => {
  const queries = queryClient.getQueriesData({ queryKey: playlistKeys.listPrefix });
  queries.forEach(([queryKey, data]) => {
    if (!data) return;
    const nextData = updater(data);
    queryClient.setQueryData(queryKey, nextData);
  });
};

export const usePlaylistMutations = () => {
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (payload) => createPlaylistApi(payload),
    onMutate: async (payload) => {
      await queryClient.cancelQueries({ queryKey: playlistKeys.listPrefix });
      const optimisticId = `temp-${Date.now()}`;
      const timestamp = nowIso();
      const optimisticPlaylist = {
        id: optimisticId,
        name: payload.name,
        description: payload.description ?? null,
        created_at: timestamp,
        updated_at: timestamp,
        tracks: payload.tracks ?? [],
      };

      const listKey = playlistKeys.list(1, PLAYLIST_DEFAULT_PAGE_SIZE);
      const previousList = queryClient.getQueryData(listKey);
      if (previousList) {
        const perPage = previousList.pagination?.per_page || PLAYLIST_DEFAULT_PAGE_SIZE;
        const nextItems = [optimisticPlaylist, ...(previousList.items || [])].slice(
          0,
          perPage,
        );
        queryClient.setQueryData(listKey, {
          ...previousList,
          items: nextItems,
          pagination: previousList.pagination
            ? {
                ...previousList.pagination,
                total: (previousList.pagination.total || 0) + 1,
              }
            : undefined,
        });
      }

      queryClient.setQueryData(playlistKeys.detail(optimisticId), optimisticPlaylist);

      return { previousList, optimisticId };
    },
    onError: (_error, _payload, context) => {
      if (context?.previousList) {
        queryClient.setQueryData(
          playlistKeys.list(1, PLAYLIST_DEFAULT_PAGE_SIZE),
          context.previousList,
        );
      }
    },
    onSuccess: (response, _payload, context) => {
      const playlist = response?.playlist;
      if (!playlist) {
        queryClient.invalidateQueries({ queryKey: playlistKeys.listPrefix });
        return;
      }
      queryClient.setQueryData(playlistKeys.detail(playlist.id), playlist);
      if (context?.optimisticId && playlist.id !== context.optimisticId) {
        queryClient.removeQueries({ queryKey: playlistKeys.detail(context.optimisticId) });
      }

      const listKey = playlistKeys.list(1, PLAYLIST_DEFAULT_PAGE_SIZE);
      const existing = queryClient.getQueryData(listKey);
      if (existing) {
        const perPage = existing.pagination?.per_page || PLAYLIST_DEFAULT_PAGE_SIZE;
        const filtered = (existing.items || []).filter(
          (item) => item.id !== context?.optimisticId && item.id !== playlist.id,
        );
        queryClient.setQueryData(listKey, {
          ...existing,
          items: [playlist, ...filtered].slice(0, perPage),
        });
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: playlistKeys.listPrefix });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => updatePlaylistApi(id, data),
    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({ queryKey: playlistKeys.detail(id) });
      const previousDetail = queryClient.getQueryData(playlistKeys.detail(id));
      if (previousDetail) {
        const optimistic = {
          ...previousDetail,
          ...data,
          updated_at: nowIso(),
        };
        queryClient.setQueryData(playlistKeys.detail(id), optimistic);
        applyToListCaches(queryClient, (old) => {
          const items = old.items || [];
          const idx = items.findIndex((item) => item.id === id);
          if (idx === -1) return old;
          const nextItems = [...items];
          nextItems[idx] = { ...nextItems[idx], ...optimistic };
          return { ...old, items: nextItems };
        });
      }

      return { previousDetail };
    },
    onError: (_error, variables, context) => {
      if (context?.previousDetail) {
        queryClient.setQueryData(playlistKeys.detail(variables.id), context.previousDetail);
        applyToListCaches(queryClient, (old) => {
          const items = old.items || [];
          const idx = items.findIndex((item) => item.id === variables.id);
          if (idx === -1) return old;
          const nextItems = [...items];
          nextItems[idx] = { ...nextItems[idx], ...context.previousDetail };
          return { ...old, items: nextItems };
        });
      }
    },
    onSuccess: (response) => {
      const playlist = response?.playlist;
      if (!playlist) {
        return;
      }
      queryClient.setQueryData(playlistKeys.detail(playlist.id), playlist);
      applyToListCaches(queryClient, (old) => {
        const items = old.items || [];
        const idx = items.findIndex((item) => item.id === playlist.id);
        if (idx === -1) return old;
        const nextItems = [...items];
        nextItems[idx] = { ...nextItems[idx], ...playlist };
        return { ...old, items: nextItems };
      });
    },
    onSettled: (response, _error, variables) => {
      queryClient.invalidateQueries({ queryKey: playlistKeys.detail(variables.id) });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => deletePlaylistApi(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: playlistKeys.listPrefix });
      const previousLists = queryClient.getQueriesData({ queryKey: playlistKeys.listPrefix });
      const previousDetail = queryClient.getQueryData(playlistKeys.detail(id));
      applyToListCaches(queryClient, (old) => {
        const items = old.items || [];
        const nextItems = items.filter((item) => item.id !== id);
        if (nextItems.length === items.length) return old;
        return {
          ...old,
          items: nextItems,
          pagination: old.pagination
            ? {
                ...old.pagination,
                total: Math.max((old.pagination.total || 1) - 1, 0),
              }
            : undefined,
        };
      });
      return { previousLists, previousDetail };
    },
    onError: (_error, id, context) => {
      if (context?.previousLists) {
        context.previousLists.forEach(([key, data]) => {
          queryClient.setQueryData(key, data);
        });
      }
      if (context?.previousDetail) {
        queryClient.setQueryData(playlistKeys.detail(id), context.previousDetail);
      }
    },
    onSuccess: (_response, id) => {
      queryClient.removeQueries({ queryKey: playlistKeys.detail(id) });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: playlistKeys.listPrefix });
    },
  });

  const addTracksMutation = useMutation({
    mutationFn: ({ id, tracks }) => addTracksToPlaylist(id, tracks),
    onMutate: async ({ id, tracks }) => {
      await queryClient.cancelQueries({ queryKey: playlistKeys.detail(id) });
      const previousDetail = queryClient.getQueryData(playlistKeys.detail(id));
      if (previousDetail) {
        const timestamp = nowIso();
        const existingTracks = previousDetail.tracks || [];
        const optimisticTracks = tracks.map((track, index) => ({
          id: `temp-${Date.now()}-${index}`,
          playlist_id: id,
          track,
          position: existingTracks.length + index,
          added_at: timestamp,
        }));
        queryClient.setQueryData(playlistKeys.detail(id), {
          ...previousDetail,
          tracks: [...existingTracks, ...optimisticTracks],
          updated_at: timestamp,
        });
      }
      return { previousDetail };
    },
    onError: (_error, variables, context) => {
      if (context?.previousDetail) {
        queryClient.setQueryData(playlistKeys.detail(variables.id), context.previousDetail);
      }
    },
    onSuccess: (response) => {
      const playlist = response?.playlist;
      if (!playlist) {
        return;
      }
      queryClient.setQueryData(playlistKeys.detail(playlist.id), playlist);
      applyToListCaches(queryClient, (old) => {
        const items = old.items || [];
        const idx = items.findIndex((item) => item.id === playlist.id);
        if (idx === -1) return old;
        const nextItems = [...items];
        nextItems[idx] = { ...nextItems[idx], ...playlist };
        return { ...old, items: nextItems };
      });
    },
  });

  const removeTrackMutation = useMutation({
    mutationFn: ({ id, entryId }) => removeTrackFromPlaylist(id, entryId),
    onMutate: async ({ id, entryId }) => {
      await queryClient.cancelQueries({ queryKey: playlistKeys.detail(id) });
      const previousDetail = queryClient.getQueryData(playlistKeys.detail(id));
      if (previousDetail) {
        const nextTracks = (previousDetail.tracks || []).filter((track) => track.id !== entryId);
        queryClient.setQueryData(playlistKeys.detail(id), {
          ...previousDetail,
          tracks: nextTracks.map((track, index) => ({ ...track, position: index })),
          updated_at: nowIso(),
        });
      }
      return { previousDetail };
    },
    onError: (_error, variables, context) => {
      if (context?.previousDetail) {
        queryClient.setQueryData(playlistKeys.detail(variables.id), context.previousDetail);
      }
    },
    onSuccess: (response) => {
      const playlist = response?.playlist;
      if (!playlist) {
        return;
      }
      queryClient.setQueryData(playlistKeys.detail(playlist.id), playlist);
      applyToListCaches(queryClient, (old) => {
        const items = old.items || [];
        const idx = items.findIndex((item) => item.id === playlist.id);
        if (idx === -1) return old;
        const nextItems = [...items];
        nextItems[idx] = { ...nextItems[idx], ...playlist };
        return { ...old, items: nextItems };
      });
    },
  });

  const reorderMutation = useMutation({
    mutationFn: ({ id, order }) => reorderPlaylistTracks(id, order),
    onMutate: async ({ id, order }) => {
      await queryClient.cancelQueries({ queryKey: playlistKeys.detail(id) });
      const previousDetail = queryClient.getQueryData(playlistKeys.detail(id));
      if (previousDetail) {
        const trackMap = new Map((previousDetail.tracks || []).map((track) => [track.id, track]));
        const reordered = order
          .map((entryId) => trackMap.get(entryId))
          .filter(Boolean)
          .map((track, index) => ({ ...track, position: index }));
        const remaining = (previousDetail.tracks || [])
          .filter((track) => !order.includes(track.id))
          .map((track, index) => ({ ...track, position: order.length + index }));
        queryClient.setQueryData(playlistKeys.detail(id), {
          ...previousDetail,
          tracks: [...reordered, ...remaining],
          updated_at: nowIso(),
        });
      }
      return { previousDetail };
    },
    onError: (_error, variables, context) => {
      if (context?.previousDetail) {
        queryClient.setQueryData(playlistKeys.detail(variables.id), context.previousDetail);
      }
    },
    onSuccess: (response) => {
      const playlist = response?.playlist;
      if (!playlist) {
        return;
      }
      queryClient.setQueryData(playlistKeys.detail(playlist.id), playlist);
    },
  });

  return useMemo(
    () => ({
      createPlaylist: (payload) => createMutation.mutateAsync(payload),
      updatePlaylist: (id, data) => updateMutation.mutateAsync({ id, data }),
      deletePlaylist: (id) => deleteMutation.mutateAsync(id),
      addTracks: (id, tracks) => addTracksMutation.mutateAsync({ id, tracks }),
      removeTrack: (id, entryId) => removeTrackMutation.mutateAsync({ id, entryId }),
      reorderTracks: (id, order) => reorderMutation.mutateAsync({ id, order }),
      states: {
        create: createMutation,
        update: updateMutation,
        delete: deleteMutation,
        addTracks: addTracksMutation,
        removeTrack: removeTrackMutation,
        reorder: reorderMutation,
      },
    }),
    [
      addTracksMutation,
      createMutation,
      deleteMutation,
      removeTrackMutation,
      reorderMutation,
      updateMutation,
    ],
  );
};

export default {
  playlistKeys,
  usePlaylistList,
  usePlaylist,
  usePlaylistMutations,
};
