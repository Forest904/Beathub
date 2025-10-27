import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import PlaylistCreateForm from '../components/PlaylistCreateForm.jsx';
import PlaylistDetail from '../components/PlaylistDetail.jsx';
import PlaylistList from '../components/PlaylistList.jsx';
import {
  PLAYLIST_DEFAULT_PAGE_SIZE,
  usePlaylist,
  usePlaylistList,
  usePlaylistMutations,
} from '../hooks/usePlaylists';
import { useAuth } from '../../../shared/hooks/useAuth';

const MyPlaylistsPage = () => {
  const { user, loading } = useAuth();
  const [page, setPage] = useState(1);
  const perPage = PLAYLIST_DEFAULT_PAGE_SIZE;
  const [selectedId, setSelectedId] = useState(null);
  const [formError, setFormError] = useState('');
  const listContainerRef = useRef(null);
  const detailContainerRef = useRef(null);

  const listQuery = usePlaylistList({ page, perPage });
  const playlists = listQuery.data?.items || [];
  const pagination = listQuery.data?.pagination || {};

  useEffect(() => {
    if (!playlists.length) {
      setSelectedId(null);
      return;
    }

    if (selectedId && !playlists.some((item) => item.id === selectedId)) {
      setSelectedId(null);
    }
  }, [playlists, selectedId]);

  useEffect(() => {
    if (!selectedId) {
      return undefined;
    }

    const handleClickAway = (event) => {
      const listEl = listContainerRef.current;
      const detailEl = detailContainerRef.current;

      if (listEl?.contains(event.target) || detailEl?.contains(event.target)) {
        return;
      }

      setSelectedId(null);
    };

    document.addEventListener('click', handleClickAway);
    return () => {
      document.removeEventListener('click', handleClickAway);
    };
  }, [selectedId]);

  const detailQuery = usePlaylist(selectedId);
  const playlist = detailQuery.data;

  const mutations = usePlaylistMutations();

  const handleCreatePlaylist = async (payload) => {
    try {
      const response = await mutations.createPlaylist(payload);
      const newId = response?.playlist?.id;
      if (newId) {
        setSelectedId(newId);
      }
      setFormError('');
    } catch (error) {
      console.error('Failed to create playlist', error);
      setFormError('Unable to create playlist. Please try again.');
    }
  };

  const handleDeletePlaylist = async (item) => {
    try {
      await mutations.deletePlaylist(item.id);
      if (selectedId === item.id) {
        setSelectedId(null);
      }
    } catch (error) {
      console.error('Failed to delete playlist', error);
    }
  };

  const handleRemoveTrack = async (entry) => {
    if (!selectedId) return;
    await mutations.removeTrack(selectedId, entry.id);
  };

  const handleReorderTracks = async (order) => {
    if (!selectedId) return;
    await mutations.reorderTracks(selectedId, order);
  };

  const handleSelectPlaylist = (item) => {
    setSelectedId((current) => (current === item.id ? null : item.id));
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-50 dark:bg-slate-950">
        <p className="text-slate-600 dark:text-gray-300">Loading your playlists...</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-50 dark:bg-slate-950">
        <div className="rounded-2xl bg-white p-8 text-center shadow ring-1 ring-brand-100 dark:bg-gray-900 dark:text-gray-200 dark:ring-gray-700">
          <h1 className="mb-4 text-3xl font-semibold text-slate-900 dark:text-white">Sign in required</h1>
          <p className="mb-6 text-slate-600 dark:text-gray-400">
            Log in to create playlists and manage your favourite tracks.
          </p>
          <Link
            to="/login"
            className="rounded-full bg-brand-600 px-4 py-2 font-medium text-white transition hover:bg-brand-500 dark:bg-brandDark-500 dark:hover:bg-brandDark-400"
          >
            Go to login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-brand-50 py-8 dark:bg-slate-950">
      <div className="mx-auto max-w-7xl space-y-6 px-4">
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-4">
            <PlaylistCreateForm
              onCreate={handleCreatePlaylist}
              isSubmitting={mutations.states.create.isPending}
            />
            {formError && (
              <p className="rounded-lg bg-brandError-100 p-3 text-sm text-brandError-700 dark:bg-brandError-900/40 dark:text-brandError-300">
                {formError}
              </p>
            )}
          </div>

          <div
            ref={listContainerRef}
            className="rounded-2xl bg-white p-6 shadow ring-1 ring-brand-100 dark:bg-gray-900 dark:ring-gray-700"
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Your playlists</h2>
              <span className="text-sm text-slate-500 dark:text-gray-400">
                Page {pagination.page || 1} / {pagination.pages || 1}
              </span>
            </div>
            {listQuery.isLoading ? (
              <p className="text-sm text-slate-600 dark:text-gray-300">Loading playlists...</p>
            ) : (
              <PlaylistList
                playlists={playlists}
                activePlaylistId={selectedId}
                onSelect={handleSelectPlaylist}
                onDelete={handleDeletePlaylist}
              />
            )}
            <div className="mt-4 flex items-center justify-between text-sm text-slate-600 dark:text-gray-400">
              <button
                type="button"
                onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                disabled={!pagination.has_prev}
                className={`rounded-full px-3 py-1 font-medium ${
                  pagination.has_prev
                    ? 'bg-brand-600 text-white hover:bg-brand-500 dark:bg-brandDark-500 dark:hover:bg-brandDark-400'
                    : 'bg-slate-200 text-slate-500 dark:bg-gray-700 dark:text-gray-500'
                }`}
              >
                Previous
              </button>
              <button
                type="button"
                onClick={() => setPage((prev) => (pagination.has_next ? prev + 1 : prev))}
                disabled={!pagination.has_next}
                className={`rounded-full px-3 py-1 font-medium ${
                  pagination.has_next
                    ? 'bg-brand-600 text-white hover:bg-brand-500 dark:bg-brandDark-500 dark:hover:bg-brandDark-400'
                    : 'bg-slate-200 text-slate-500 dark:bg-gray-700 dark:text-gray-500'
                }`}
              >
                Next
              </button>
            </div>
          </div>
        </div>

        {selectedId && (
          <div ref={detailContainerRef}>
            {detailQuery.isLoading ? (
              <div className="rounded-2xl bg-white p-6 text-center text-slate-600 shadow ring-1 ring-brand-100 dark:bg-gray-900 dark:text-gray-300 dark:ring-gray-700">
                Loading playlist details...
              </div>
            ) : playlist ? (
              <PlaylistDetail
                playlist={playlist}
                onRemoveTrack={handleRemoveTrack}
                onReorderTracks={handleReorderTracks}
              />
            ) : (
              <div className="rounded-2xl bg-white p-6 text-center text-slate-600 shadow ring-1 ring-brand-100 dark:bg-gray-900 dark:text-gray-300 dark:ring-gray-700">
                We couldn't load this playlist. Try selecting another one.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default MyPlaylistsPage;

