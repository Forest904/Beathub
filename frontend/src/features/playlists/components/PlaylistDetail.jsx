import React, { useMemo } from 'react';
import PropTypes from 'prop-types';

import TrackTile from '../../../shared/components/TrackTile.jsx';

const PlaylistDetail = ({
  playlist,
  onRemoveTrack,
  onReorderTracks,
}) => {
  const orderedTracks = useMemo(() => {
    const items = playlist?.tracks || [];
    return [...items].sort((a, b) => (a.position ?? 0) - (b.position ?? 0));
  }, [playlist]);

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
            This playlist is empty. Visit Discover and use the Add to playlist option to start filling it.
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
  onRemoveTrack: PropTypes.func.isRequired,
  onReorderTracks: PropTypes.func.isRequired,
};

PlaylistDetail.defaultProps = {
  playlist: null,
};

export default PlaylistDetail;
