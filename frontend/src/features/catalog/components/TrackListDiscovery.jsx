import React, { useContext } from 'react';
import PropTypes from 'prop-types';
import { formatDuration } from '../../../shared/utils/formatting';
import CompilationContext from '../../compilations/context/CompilationContext.jsx';
import { useAuth } from '../../../shared/hooks/useAuth';

const TrackListDiscovery = ({ tracks }) => {
  const compilation = useContext(CompilationContext);
  const { user } = useAuth();
  if (!tracks || tracks.length === 0) return null;


  return (
    <ul className="space-y-2">
      {tracks.map((track, index) => {
        const id = track.spotify_id || track.id || track.url || track.uri;
        const inCart = id ? compilation?.isInCompilation(id) : false;
        const handleToggle = (e) => {
          e.stopPropagation();
          if (!id || !compilation) return;
          if (inCart) {
            compilation.remove(id);
          } else {
            compilation.add({
              spotify_id: track.spotify_id || id,
              title: track.title,
              artists: track.artists || [],
              duration_ms: track.duration_ms,
              albumId: track.albumId,
              spotify_url: track.spotify_url,
              url: track.url,
              uri: track.uri,
            });
          }
        };

        return (
          <li
            key={id || index}
            className="bg-brand-50 dark:bg-gray-800 p-4 rounded-lg shadow flex flex-col sm:flex-row justify-between items-center ring-1 ring-brand-100 dark:ring-0"
          >
            <div className="flex-1 text-left mb-2 sm:mb-0">
              <p className="text-lg font-medium text-slate-900 dark:text-white">
                {(track.track_number ?? index + 1)}. {track.title}
              </p>
              <p className="text-sm text-slate-600 dark:text-gray-400">{(track.artists || []).join(', ')}</p>
            </div>
            <div className="flex items-center gap-3">
              {user && (
                <button
                  type="button"
                  onClick={handleToggle}
                  className={`px-2 py-1 rounded text-sm ${inCart ? 'bg-brandError-600 text-white hover:bg-brandError-700' : 'bg-brand-600 text-white hover:bg-brand-700'}`}
                  title={inCart ? 'Remove from compilation' : 'Add to compilation'}
                >
                  {inCart ? 'Remove' : '+'}
                </button>
              )}
              <p className="text-slate-600 dark:text-gray-400 text-sm">{formatDuration(track.duration_ms)}</p>
            </div>
          </li>
        );
      })}
    </ul>
  );
};

TrackListDiscovery.propTypes = {
  tracks: PropTypes.arrayOf(
    PropTypes.shape({
      spotify_id: PropTypes.string,
      id: PropTypes.string,
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
