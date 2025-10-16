import React, { useEffect, useMemo, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import { usePlaylistList, usePlaylistMutations } from '../../playlists/hooks/usePlaylists';
import { useFavoriteStatus, useToggleFavorite } from '../../favorites/hooks/useFavorites';
import { useAuth } from '../../../shared/hooks/useAuth';
import TrackTile from '../../../shared/components/TrackTile.jsx';

const asArrayOfArtists = (value) => {
  if (!value) return [];
  if (Array.isArray(value)) return value.map((artist) => String(artist).trim()).filter(Boolean);
  return String(value)
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean);
};

const buildPlaylistTrackPayload = (track, fallbackId) => {
  const spotifyId = track.spotify_id || track.id || track.uri || track.url || fallbackId;
  if (!spotifyId) return null;
  const artists = asArrayOfArtists(track.artists);
  const payload = {
    spotify_id: spotifyId,
    title: track.title,
    artists,
    duration_ms: track.duration_ms,
    album_name: track.album_name || track.album?.name || track.albumName,
    album_id: track.album_id || track.albumId,
    album_artist: track.album_artist,
    track_number: track.track_number,
    disc_number: track.disc_number,
    disc_count: track.disc_count,
    spotify_url: track.spotify_url || track.url,
    url: track.url,
    uri: track.uri,
    cover_url: track.cover_url || track.image_url,
    explicit: track.explicit,
    popularity: track.popularity,
    isrc: track.isrc,
    year: track.year,
    date: track.date,
    genres: track.genres,
  };
  return Object.fromEntries(Object.entries(payload).filter(([, value]) => value !== undefined && value !== null && value !== ''));
};

const buildFavoriteMetadata = (track) => {
  const artists = asArrayOfArtists(track.artists);
  return {
    name: track.title,
    subtitle: artists.join(', '),
    cover_url: track.cover_url,
    image_url: track.image_url,
    spotify_url: track.spotify_url,
    url: track.spotify_url || track.url,
  };
};

const DiscoveryTrackActions = ({
  track,
  trackId,
  user,
  playlists,
  playlistsLoading,
  playlistsError,
  onReloadPlaylists,
  onAddToPlaylist,
  isAddingToPlaylist,
}) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const [showPlaylistPicker, setShowPlaylistPicker] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');
  const menuRef = useRef(null);
  const toggleFavorite = useToggleFavorite();
  const favoriteId = trackId ? String(trackId) : '';
  const favoriteStatus = useFavoriteStatus('track', favoriteId);

  const spotifyUrl = track.spotify_url || track.url || track.uri || '';
  const favoriteMetadata = useMemo(() => buildFavoriteMetadata(track), [track]);
  const playlistTrackPayload = useMemo(() => buildPlaylistTrackPayload(track, trackId), [track, trackId]);
  const favorited = Boolean(favoriteStatus.data?.favorited);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const handleClick = (event) => {
      if (!menuRef.current) return;
      if (!menuRef.current.contains(event.target)) {
        setMenuOpen(false);
        setShowPlaylistPicker(false);
      }
    };
    const handleKey = (event) => {
      if (event.key === 'Escape') {
        setMenuOpen(false);
        setShowPlaylistPicker(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, [menuOpen]);

  useEffect(() => {
    if (!menuOpen) {
      setFeedback('');
      setError('');
      setShowPlaylistPicker(false);
    }
  }, [menuOpen]);

  const handleOpenSpotify = () => {
    if (!spotifyUrl) return;
    window.open(spotifyUrl, '_blank', 'noopener,noreferrer');
    setMenuOpen(false);
  };

  const handleToggleFavorite = async () => {
    if (!favoriteId) return;
    try {
      await toggleFavorite.mutateAsync({
        item_type: 'track',
        item_id: favoriteId,
        metadata: favoriteMetadata,
      });
      setFeedback(favorited ? 'Removed from favourites.' : 'Added to favourites.');
    } catch (err) {
      console.error('Failed to toggle favourite', err);
      setError('Could not update favourites.');
    }
  };

  const handleShowPlaylists = async () => {
    if (!showPlaylistPicker && typeof onReloadPlaylists === 'function') {
      try {
        await onReloadPlaylists();
      } catch (err) {
        console.error('Failed to refresh playlists', err);
      }
    }
    setShowPlaylistPicker((prev) => !prev);
  };

  const handleAddToPlaylist = async (playlist) => {
    if (!playlist?.id || !playlistTrackPayload || typeof onAddToPlaylist !== 'function') {
      return;
    }
    setError('');
    try {
      await onAddToPlaylist(playlist.id, playlistTrackPayload);
      setFeedback(`Added to "${playlist.name}".`);
      setShowPlaylistPicker(false);
    } catch (err) {
      console.error('Failed to add track to playlist', err);
      setError('Could not add track to playlist.');
    }
  };

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        onClick={(event) => {
          event.stopPropagation();
          setMenuOpen((prev) => !prev);
        }}
        className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-200 text-lg font-semibold text-slate-700 transition hover:bg-slate-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
        title="Track actions"
        aria-haspopup="menu"
        aria-expanded={menuOpen}
      >
        ⋯
      </button>
      {menuOpen && (
        <div className="absolute right-0 z-20 mt-2 w-60 rounded-lg bg-white shadow-lg ring-1 ring-black/5 dark:bg-gray-900 dark:ring-gray-700">
          <ul className="py-1 text-sm text-slate-700 dark:text-gray-200">
            <li>
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  handleOpenSpotify();
                }}
                disabled={!spotifyUrl}
                className="flex w-full items-center gap-2 px-4 py-2 text-left transition hover:bg-brand-50 disabled:cursor-not-allowed disabled:text-slate-400 dark:hover:bg-gray-800 dark:disabled:text-gray-600"
              >
                Open on Spotify
              </button>
            </li>
            {user ? (
              <>
                <li>
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      handleToggleFavorite();
                    }}
                    disabled={!favoriteId || toggleFavorite.isPending}
                    className="flex w-full items-center gap-2 px-4 py-2 text-left transition hover:bg-brand-50 disabled:cursor-not-allowed disabled:text-slate-400 dark:hover:bg-gray-800 dark:disabled:text-gray-600"
                  >
                    {favorited ? 'Remove from favourites' : 'Add to favourites'}
                  </button>
                </li>
                <li className="px-4 py-1">
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      handleShowPlaylists();
                    }}
                    disabled={!playlistTrackPayload}
                    className="w-full rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-brand-500 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500 dark:bg-brandDark-500 dark:hover:bg-brandDark-400"
                  >
                    Add to playlist
                  </button>
                  {showPlaylistPicker && (
                    <div className="mt-2 max-h-64 overflow-y-auto rounded-md border border-slate-200 bg-white shadow-inner dark:border-gray-700 dark:bg-gray-800">
                      {playlistsLoading ? (
                        <p className="px-3 py-2 text-sm text-slate-500 dark:text-gray-400">Loading playlists…</p>
                      ) : playlistsError ? (
                        <div className="space-y-2 px-3 py-2 text-sm">
                          <p className="text-brandError-600 dark:text-brandError-400">Failed to load playlists.</p>
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              if (typeof onReloadPlaylists === 'function') {
                                onReloadPlaylists();
                              }
                            }}
                            className="text-brand-600 underline transition hover:text-brand-500 dark:text-brandDark-300 dark:hover:text-brandDark-200"
                          >
                            Try again
                          </button>
                        </div>
                      ) : playlists.length === 0 ? (
                        <div className="space-y-2 px-3 py-2 text-sm text-slate-600 dark:text-gray-300">
                          <p>You don’t have any playlists yet.</p>
                          <Link
                            to="/playlists"
                            className="inline-flex items-center gap-1 text-brand-600 underline transition hover:text-brand-500 dark:text-brandDark-300 dark:hover:text-brandDark-200"
                            onClick={() => setMenuOpen(false)}
                          >
                            Create your first playlist
                          </Link>
                        </div>
                      ) : (
                        <ul className="divide-y divide-slate-200 dark:divide-gray-700">
                          {playlists.map((playlist) => (
                            <li key={playlist.id}>
                              <button
                                type="button"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  handleAddToPlaylist(playlist);
                                }}
                                disabled={isAddingToPlaylist}
                                className="flex w-full items-start justify-between gap-2 px-3 py-2 text-left transition hover:bg-brand-50 disabled:cursor-not-allowed disabled:text-slate-400 dark:hover:bg-gray-700 dark:disabled:text-gray-500"
                              >
                                <span className="truncate">{playlist.name}</span>
                                {isAddingToPlaylist && <span className="text-xs text-slate-400 dark:text-gray-500">Adding…</span>}
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </li>
              </>
            ) : (
              <li className="px-4 py-2 text-xs text-slate-500 dark:text-gray-400">Sign in to add favourites and playlists.</li>
            )}
          </ul>
          {(feedback || error) && (
            <div className="border-t border-slate-200 px-4 py-2 text-xs dark:border-gray-700">
              {feedback && <p className="text-brand-600 dark:text-brandDark-300">{feedback}</p>}
              {error && <p className="text-brandError-600 dark:text-brandError-400">{error}</p>}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

DiscoveryTrackActions.propTypes = {
  track: PropTypes.object.isRequired,
  trackId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  user: PropTypes.object,
  playlists: PropTypes.arrayOf(PropTypes.object),
  playlistsLoading: PropTypes.bool,
  playlistsError: PropTypes.bool,
  onReloadPlaylists: PropTypes.func,
  onAddToPlaylist: PropTypes.func,
  isAddingToPlaylist: PropTypes.bool,
};

DiscoveryTrackActions.defaultProps = {
  trackId: undefined,
  user: null,
  playlists: [],
  playlistsLoading: false,
  playlistsError: false,
  onReloadPlaylists: undefined,
  onAddToPlaylist: undefined,
  isAddingToPlaylist: false,
};

const TrackListDiscovery = ({ tracks }) => {
  const { user } = useAuth();
  const playlistQuery = usePlaylistList({ page: 1, perPage: 50 });
  const playlistMutations = usePlaylistMutations();
  if (!tracks || tracks.length === 0) return null;


  return (
    <ul className="space-y-2">
      {tracks.map((track, index) => {
        const id = track.spotify_id || track.id || track.url || track.uri;
        return (
          <TrackTile
            key={id || index}
            track={track}
            index={index}
            renderActions={() => (
              <DiscoveryTrackActions
                track={track}
                trackId={id}
                user={user}
                playlists={playlistQuery.data?.items || []}
                playlistsLoading={playlistQuery.isLoading || playlistQuery.isFetching}
                playlistsError={Boolean(playlistQuery.isError)}
                onReloadPlaylists={playlistQuery.refetch}
                onAddToPlaylist={(playlistId, playlistTrack) => playlistMutations.addTracks(playlistId, [playlistTrack])}
                isAddingToPlaylist={playlistMutations.states.addTracks.isPending}
              />
            )}
            showFavorite={false}
          />
        );
      })}
    </ul>
  );
};

TrackListDiscovery.propTypes = {
  tracks: PropTypes.arrayOf(
    PropTypes.shape({
      spotify_id: PropTypes.string,
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
      url: PropTypes.string,
      uri: PropTypes.string,
      title: PropTypes.string.isRequired,
      artists: PropTypes.arrayOf(PropTypes.string),
      duration_ms: PropTypes.number,
      albumId: PropTypes.string,
      track_number: PropTypes.number,
      spotify_url: PropTypes.string,
    }),
  ),
};

TrackListDiscovery.defaultProps = {
  tracks: [],
};

export default TrackListDiscovery;
