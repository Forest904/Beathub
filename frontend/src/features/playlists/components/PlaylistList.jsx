import React from 'react';
import PropTypes from 'prop-types';

const PlaylistList = ({ playlists, activePlaylistId, onSelect, onDelete }) => {
  if (!playlists || playlists.length === 0) {
    return (
      <div className="rounded-2xl bg-white p-6 text-center text-slate-600 shadow ring-1 ring-brand-100 dark:bg-gray-900 dark:text-gray-300 dark:ring-gray-700">
        No playlists yet. Use the form to create your first collection.
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {playlists.map((playlist) => {
        const isActive = playlist.id === activePlaylistId;
        const trackCount = Array.isArray(playlist.tracks)
          ? playlist.tracks.length
          : playlist.track_count ?? 0;
        return (
          <li key={playlist.id}>
            <button
              type="button"
              onClick={() => onSelect(playlist)}
              aria-pressed={isActive}
              className={`flex w-full items-center justify-between rounded-2xl border px-4 py-3 text-left transition ${
                isActive
                  ? 'border-brand-500 bg-brand-100 text-brand-800 shadow-sm dark:border-brandDark-400 dark:bg-brandDark-900/40 dark:text-brandDark-200'
                  : 'border-transparent bg-white text-slate-800 hover:border-brand-200 hover:bg-brand-50 dark:bg-gray-900 dark:text-gray-100 dark:hover:border-brandDark-500/40 dark:hover:bg-gray-800'
              }`}
            >
              <div>
                <h3 className="text-lg font-semibold">{playlist.name}</h3>
                {playlist.description && (
                  <p className="text-sm text-slate-600 dark:text-gray-400">
                    {playlist.description}
                  </p>
                )}
                <p className="text-xs text-slate-500 dark:text-gray-500">
                  Updated {new Date(playlist.updated_at).toLocaleString()}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="rounded-full bg-brand-600 px-3 py-1 text-sm font-semibold text-white dark:bg-brandDark-500">
                  {trackCount} tracks
                </span>
                {typeof onDelete === 'function' && (
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onDelete(playlist);
                    }}
                    className="rounded-full bg-brandError-600 px-3 py-1 text-sm font-medium text-white hover:bg-brandError-500 dark:bg-brandError-500 dark:hover:bg-brandError-400"
                  >
                    Delete
                  </button>
                )}
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
};

PlaylistList.propTypes = {
  playlists: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      name: PropTypes.string.isRequired,
      description: PropTypes.string,
      updated_at: PropTypes.string,
      tracks: PropTypes.array,
      track_count: PropTypes.number,
    }),
  ),
  activePlaylistId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  onSelect: PropTypes.func.isRequired,
  onDelete: PropTypes.func,
};

PlaylistList.defaultProps = {
  playlists: [],
  activePlaylistId: undefined,
  onDelete: undefined,
};

export default PlaylistList;
