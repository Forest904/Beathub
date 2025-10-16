import { endpoints } from '../../api/client';
import { del, get, post, put } from '../../api/http';

export const fetchPlaylists = (params) =>
  get(endpoints.playlists.list(), { params });

export const fetchPlaylist = (id) =>
  get(endpoints.playlists.detail(id));

export const createPlaylist = (payload) =>
  post(endpoints.playlists.list(), payload);

export const updatePlaylist = (id, payload) =>
  put(endpoints.playlists.detail(id), payload);

export const deletePlaylist = (id) => del(endpoints.playlists.detail(id));

export const addTracksToPlaylist = (id, tracks) =>
  post(endpoints.playlists.tracks(id), { tracks });

export const removeTrackFromPlaylist = (id, entryId) =>
  del(`${endpoints.playlists.tracks(id)}/${entryId}`);

export const reorderPlaylistTracks = (id, order) =>
  put(endpoints.playlists.reorder(id), { order });

export default {
  fetchPlaylists,
  fetchPlaylist,
  createPlaylist,
  updatePlaylist,
  deletePlaylist,
  addTracksToPlaylist,
  removeTrackFromPlaylist,
  reorderPlaylistTracks,
};
