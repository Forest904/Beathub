import React, { useMemo, useState } from 'react';
import PropTypes from 'prop-types';

import TrackTile from '../../../shared/components/TrackTile.jsx';

const emptyTrack = {
  title: '',
  artists: '',
  spotify_id: '',
  duration_ms: '',
  album_name: '',
};

const PlaylistDetail = ({
  playlist,
  onAddTrack,
  onRemoveTrack,
  onReorderTracks,
  isMutating,
}) => {
  const [draftTrack, setDraftTrack] = useState(emptyTrack);
  const [error, setError] = useState('');

  const orderedTracks = useMemo(() => {
    const items = playlist?.tracks || [];
    return [...items].sort((a, b) => (a.position ?? 0) - (b.position ?? 0));
  }, [playlist]);

  const handleInputChange = (field) => (event) => {
    setDraftTrack((current) => ({ ...current, [field]: event.target.value }));
  };

  const handleAddTrack = async (event) => {
    event.preventDefault();
    const title = draftTrack.title.trim();
    const spotifyId = draftTrack.spotify_id.trim();
    if (!title || !spotifyId) {
      setError('Provide at least a title and Spotify ID to add a track.');
      return;
    }
    const payload = {
      title,
      spotify_id: spotifyId,
      artists: draftTrack.artists
        .split(',')
        .map((value) => value.trim())
        .filter(Boolean),
      duration_ms: draftTrack.duration_ms ? Number(draftTrack.duration_ms) : undefined,
      album_name: draftTrack.album_name.trim() || undefined,
    };
    setError('');
    await onAddTrack(payload);
    setDraftTrack(emptyTrack);
  };

  const moveTrack = (entryId, direction) => {
    const currentOrder = orderedTracks.map((entry) => entry.id);
    const index = currentOrder.indexOf(entryId);
    if (index === -1) return;
    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === currentOrder.length - 1) return;
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    const nextOrder = [...currentOrder];
    const [moved] = nextOrder.splice(index, 1);
    nextOrder.splice(targetIndex, 0, moved);
    onReorderTracks(nextOrder);
  };

  return (
    <div className="space-y-6 rounded-2xl bg-white p-6 shadow ring-1 ring-brand-100 dark:bg-gray-900 dark:ring-gray-700">
      <header className="flex flex-col gap-2">
        <h2 className="text-3xl font-bold text-slate-900 dark:text-white">
          {playlist?.name || 'Playlist'}
        </h2>
        {playlist?.description && (
          <p className="text-slate-600 dark:text-gray-400">{playlist.description}</p>
        )}
        <p className="text-sm text-slate-500 dark:text-gray-500">
          Created {playlist?.created_at ? new Date(playlist.created_at).toLocaleString() : 'recently'}
        </p>
      </header>

      <section className="space-y-4">
        <h3 className="text-xl font-semibold text-slate-900 dark:text-white">Tracks</h3>
        {orderedTracks.length === 0 ? (
          <p className="rounded-lg bg-brand-50 p-4 text-sm text-slate-600 dark:bg-gray-800 dark:text-gray-300">
            This playlist is empty. Add a track using the form below.
          </p>
        ) : (
          <ul className="space-y-3">
            {orderedTracks.map((entry, index) => {
              const track = entry.track || entry.track_snapshot || entry;
              return (
                <TrackTile
                  key={entry.id}
                  track={track}
                  index={index}
                  renderActions={() => (
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => moveTrack(entry.id, 'up')}
                        className="rounded-full bg-slate-200 px-2 py-1 text-sm text-slate-700 hover:bg-slate-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
                        disabled={index === 0}
                      >
                        ↑
                      </button>
                      <button
                        type="button"
                        onClick={() => moveTrack(entry.id, 'down')}
                        className="rounded-full bg-slate-200 px-2 py-1 text-sm text-slate-700 hover:bg-slate-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
                        disabled={index === orderedTracks.length - 1}
                      >
                        ↓
                      </button>
                      <button
                        type="button"
                        onClick={() => onRemoveTrack(entry)}
                        className="rounded-full bg-brandError-600 px-3 py-1 text-sm font-medium text-white hover:bg-brandError-500 dark:bg-brandError-500 dark:hover:bg-brandError-400"
                      >
                        Remove
                      </button>
                    </div>
                  )}
                />
              );
            })}
          </ul>
        )}
      </section>

      <section>
        <h3 className="text-xl font-semibold text-slate-900 dark:text-white">Add track manually</h3>
        <form className="mt-4 grid gap-4 md:grid-cols-2" onSubmit={handleAddTrack}>
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-gray-300">
            Title
            <input
              type="text"
              value={draftTrack.title}
              onChange={handleInputChange('title')}
              required
              className="rounded-lg border border-slate-200 px-3 py-2 text-slate-900 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100"
              placeholder="Song title"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-gray-300">
            Spotify ID
            <input
              type="text"
              value={draftTrack.spotify_id}
              onChange={handleInputChange('spotify_id')}
              required
              className="rounded-lg border border-slate-200 px-3 py-2 text-slate-900 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100"
              placeholder="e.g. 4uLU6hMCjMI75M1A2tKUQC"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-gray-300">
            Artists (comma separated)
            <input
              type="text"
              value={draftTrack.artists}
              onChange={handleInputChange('artists')}
              className="rounded-lg border border-slate-200 px-3 py-2 text-slate-900 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100"
              placeholder="Artist 1, Artist 2"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-gray-300">
            Duration (ms)
            <input
              type="number"
              value={draftTrack.duration_ms}
              onChange={handleInputChange('duration_ms')}
              className="rounded-lg border border-slate-200 px-3 py-2 text-slate-900 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100"
              placeholder="210000"
            />
          </label>
          <label className="md:col-span-2 flex flex-col gap-1 text-sm font-medium text-slate-700 dark:text-gray-300">
            Album name (optional)
            <input
              type="text"
              value={draftTrack.album_name}
              onChange={handleInputChange('album_name')}
              className="rounded-lg border border-slate-200 px-3 py-2 text-slate-900 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100"
              placeholder="Album title"
            />
          </label>
          {error && (
            <p className="md:col-span-2 text-sm text-brandError-600 dark:text-brandError-400">{error}</p>
          )}
          <div className="md:col-span-2 flex justify-end">
            <button
              type="submit"
              className="rounded-full bg-brand-600 px-4 py-2 font-medium text-white transition hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-brandDark-500 dark:hover:bg-brandDark-400"
              disabled={isMutating}
            >
              {isMutating ? 'Adding…' : 'Add track'}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
};

PlaylistDetail.propTypes = {
  playlist: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    name: PropTypes.string,
    description: PropTypes.string,
    created_at: PropTypes.string,
    tracks: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
        position: PropTypes.number,
        track: PropTypes.object,
        track_snapshot: PropTypes.object,
      }),
    ),
  }),
  onAddTrack: PropTypes.func.isRequired,
  onRemoveTrack: PropTypes.func.isRequired,
  onReorderTracks: PropTypes.func.isRequired,
  isMutating: PropTypes.bool,
};

PlaylistDetail.defaultProps = {
  playlist: null,
  isMutating: false,
};

export default PlaylistDetail;
