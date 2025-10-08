import { useEffect } from 'react';
import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';

import {
  fetchFavoriteStatus,
  fetchFavorites,
  fetchFavoriteSummary,
  removeFavorite as removeFavoriteApi,
  toggleFavorite as toggleFavoriteApi,
} from '../api';
import { useAuth } from '../../../shared/hooks/useAuth';
import { FAVORITE_TYPES } from '../../../theme/tokens';

export const favoriteKeys = {
  all: ['favorites'],
  listPrefix: ['favorites', 'list'],
  list: (type, page, perPage) => [
    'favorites',
    'list',
    type || 'all',
    page || 1,
    perPage || 20,
  ],
  summary: ['favorites', 'summary'],
  status: (type, id) => ['favorites', 'status', type || 'unknown', id || 'unknown'],
};

const favoriteEvents = new EventTarget();
const FAVORITE_EVENT_NAME = 'favorite-change';

export const emitFavoriteChange = (detail) => {
  favoriteEvents.dispatchEvent(new CustomEvent(FAVORITE_EVENT_NAME, { detail }));
};

export const useFavoriteEvents = (handler) => {
  useEffect(() => {
    if (typeof handler !== 'function') return undefined;
    const listener = (event) => handler(event.detail);
    favoriteEvents.addEventListener(FAVORITE_EVENT_NAME, listener);
    return () => favoriteEvents.removeEventListener(FAVORITE_EVENT_NAME, listener);
  }, [handler]);
};

export const useFavoritesList = ({ page = 1, perPage = 20, type } = {}) => {
  const { user } = useAuth();
  return useQuery({
    queryKey: favoriteKeys.list(type, page, perPage),
    queryFn: () =>
      fetchFavorites({
        page,
        per_page: perPage,
        type: FAVORITE_TYPES.includes(type) ? type : undefined,
      }),
    enabled: Boolean(user),
    staleTime: 1000 * 30,
    keepPreviousData: true,
  });
};

export const useFavoriteSummary = () => {
  const { user } = useAuth();
  return useQuery({
    queryKey: favoriteKeys.summary,
    queryFn: fetchFavoriteSummary,
    enabled: Boolean(user),
    staleTime: 1000 * 30,
  });
};

export const useFavoriteStatus = (itemType, itemId) => {
  const { user } = useAuth();
  return useQuery({
    queryKey: favoriteKeys.status(itemType, itemId),
    queryFn: () =>
      fetchFavoriteStatus({
        item_type: itemType,
        item_id: itemId,
      }),
    enabled: Boolean(user && itemType && itemId),
    staleTime: 1000 * 30,
  });
};

export const useToggleFavorite = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (variables) => toggleFavoriteApi(variables),
    onMutate: async (variables) => {
      const { item_type: itemType, item_id: itemId } = variables;
      await Promise.all([
        queryClient.cancelQueries({ queryKey: favoriteKeys.status(itemType, itemId) }),
        queryClient.cancelQueries({ queryKey: favoriteKeys.summary }),
        queryClient.cancelQueries({ queryKey: favoriteKeys.listPrefix }),
      ]);

      const previousStatus = queryClient.getQueryData(
        favoriteKeys.status(itemType, itemId),
      );
      const previousSummary = queryClient.getQueryData(favoriteKeys.summary);

      const nextFavorited = !(previousStatus?.favorited);
      queryClient.setQueryData(favoriteKeys.status(itemType, itemId), {
        favorited: nextFavorited,
        favorite: previousStatus?.favorite ?? null,
      });

      if (previousSummary?.summary) {
        const draft = { ...previousSummary.summary };
        const key = FAVORITE_TYPES.includes(itemType) ? itemType : 'unknown';
        if (nextFavorited) {
          draft[key] = (draft[key] || 0) + 1;
          draft.total = (draft.total || 0) + 1;
        } else {
          draft[key] = Math.max((draft[key] || 1) - 1, 0);
          draft.total = Math.max((draft.total || 1) - 1, 0);
        }
        queryClient.setQueryData(favoriteKeys.summary, { summary: draft });
      }

      return { previousStatus, previousSummary };
    },
    onError: (_error, variables, context) => {
      if (context?.previousStatus) {
        queryClient.setQueryData(
          favoriteKeys.status(variables.item_type, variables.item_id),
          context.previousStatus,
        );
      }
      if (context?.previousSummary) {
        queryClient.setQueryData(favoriteKeys.summary, context.previousSummary);
      }
    },
    onSuccess: (data, variables) => {
      const { item_type: itemType, item_id: itemId } = variables;
      queryClient.setQueryData(favoriteKeys.status(itemType, itemId), {
        favorited: Boolean(data?.favorited),
        favorite: data?.favorite ?? null,
      });
      if (data?.summary) {
        queryClient.setQueryData(favoriteKeys.summary, { summary: data.summary });
      }
      queryClient.invalidateQueries({ queryKey: favoriteKeys.listPrefix });
      emitFavoriteChange({
        itemType,
        itemId,
        favorited: Boolean(data?.favorited),
        favorite: data?.favorite ?? null,
        summary: data?.summary ?? null,
      });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: favoriteKeys.summary });
    },
  });
};

export const useRemoveFavorite = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (favoriteId) => removeFavoriteApi(favoriteId),
    onSuccess: (data, favoriteId) => {
      queryClient.invalidateQueries({ queryKey: favoriteKeys.listPrefix });
      if (data?.summary) {
        queryClient.setQueryData(favoriteKeys.summary, { summary: data.summary });
      } else {
        queryClient.invalidateQueries({ queryKey: favoriteKeys.summary });
      }
      emitFavoriteChange({ favoriteId, favorited: false });
    },
  });
};

export default {
  favoriteKeys,
  useFavoritesList,
  useFavoriteSummary,
  useFavoriteStatus,
  useToggleFavorite,
  useRemoveFavorite,
  useFavoriteEvents,
};
