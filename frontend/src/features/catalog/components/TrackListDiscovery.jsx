import React, { useContext } from 'react';
import PropTypes from 'prop-types';
import CompilationContext from '../../compilations/context/CompilationContext.jsx';
import { useAuth } from '../../../shared/hooks/useAuth';
import TrackTile from '../../../shared/components/TrackTile.jsx';

const TrackListDiscovery = ({ tracks }) => {
  const compilation = useContext(CompilationContext);
  const { user } = useAuth();
  if (!tracks || tracks.length === 0) return null;


  return (
    <ul className="space-y-2">
      {tracks.map((track, index) => {
        const id = track.spotify_id || track.id || track.url || track.uri;
        const inCart = id ? compilation?.isInCompilation(id) : false;
        const renderActions = user && compilation
          ? () => {
              const handleToggle = (event) => {
                event.stopPropagation();
                if (!id) return;
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
                <button
                  type="button"
                  onClick={handleToggle}
                  className={`px-2 py-1 rounded text-sm ${
                    inCart
                      ? 'bg-brandError-600 text-white hover:bg-brandError-700'
                      : 'bg-brand-600 text-white hover:bg-brand-700'
                  }`}
                  title={inCart ? 'Remove from compilation' : 'Add to compilation'}
                >
                  {inCart ? 'Remove' : '+'}
                </button>
              );
            }
          : undefined;

        return (
          <TrackTile
            key={id || index}
            track={track}
            index={index}
            renderActions={renderActions}
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
