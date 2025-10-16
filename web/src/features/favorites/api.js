import { endpoints } from '../../api/client';
import { del, get, post } from '../../api/http';

export const fetchFavorites = (params) =>
  get(endpoints.favorites.list(), { params });

export const fetchFavoriteSummary = () => get(endpoints.favorites.summary());

export const fetchFavoriteStatus = (params) =>
  get(endpoints.favorites.status(), { params });

export const toggleFavorite = (payload) =>
  post(endpoints.favorites.toggle(), payload);

export const removeFavorite = (favoriteId) =>
  del(endpoints.favorites.remove(favoriteId));

export default {
  fetchFavorites,
  fetchFavoriteSummary,
  fetchFavoriteStatus,
  toggleFavorite,
  removeFavorite,
};
