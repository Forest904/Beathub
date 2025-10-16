import React from 'react';
import PropTypes from 'prop-types';

import FavoriteButton from '../../features/favorites/components/FavoriteButton.jsx';
import { formatDuration } from '../utils/formatting';

const TrackTile = ({
  track,
  index,
  renderActions,
  className,
  showDuration,
  showFavorite,
  favoriteItemType,
  favoriteItemId,
  favoriteMetadata,
}) => {
  if (!track) {
    return null;
  }

  const artists = Array.isArray(track.artists)
    ? track.artists
    : typeof track.artists === 'string'
      ? track.artists.split(',').map((part) => part.trim())
      : [];
  const trackNumber = track.track_number ?? index + 1;
  const durationLabel = typeof track.duration_ms === 'number'
    ? formatDuration(track.duration_ms)
    : null;

  const favoriteId = favoriteItemId
    || track.spotify_id
    || track.id
    || track.uri
    || track.url
    || '';

  const metadata = {
    name: track.title,
    subtitle: artists.join(', '),
    cover_url: track.cover_url,
    image_url: track.image_url,
    spotify_url: track.spotify_url,
    url: track.spotify_url || track.url,
    ...favoriteMetadata,
  };

  return (
    <li
      className={`flex flex-col gap-3 rounded-lg bg-brand-50 p-4 shadow transition dark:bg-gray-800 sm:flex-row sm:items-center sm:justify-between ${className}`.trim()}
    >
      <div className="flex-1">
        <p className="text-lg font-medium text-slate-900 dark:text-white">
          {trackNumber}. {track.title}
        </p>
        {artists.length > 0 && (
          <p className="text-sm text-slate-600 dark:text-gray-400">
            {artists.join(', ')}
          </p>
        )}
      </div>
      <div className="flex items-center gap-3">
        {typeof renderActions === 'function' && renderActions({ track })}
        {showFavorite && favoriteId && (
          <FavoriteButton
            itemType={favoriteItemType}
            itemId={String(favoriteId)}
            metadata={metadata}
            size="sm"
          />
        )}
        {showDuration && durationLabel && (
          <span className="text-sm text-slate-600 dark:text-gray-400">
            {durationLabel}
          </span>
        )}
      </div>
    </li>
  );
};

TrackTile.propTypes = {
  track: PropTypes.shape({
    spotify_id: PropTypes.string,
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    uri: PropTypes.string,
    url: PropTypes.string,
    title: PropTypes.string.isRequired,
    artists: PropTypes.oneOfType([
      PropTypes.arrayOf(PropTypes.string),
      PropTypes.string,
    ]),
    duration_ms: PropTypes.number,
    track_number: PropTypes.number,
    cover_url: PropTypes.string,
    image_url: PropTypes.string,
    spotify_url: PropTypes.string,
  }).isRequired,
  index: PropTypes.number,
  renderActions: PropTypes.func,
  className: PropTypes.string,
  showDuration: PropTypes.bool,
  showFavorite: PropTypes.bool,
  favoriteItemType: PropTypes.oneOf(['track', 'album', 'artist']),
  favoriteItemId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  favoriteMetadata: PropTypes.object,
};

TrackTile.defaultProps = {
  index: 0,
  renderActions: undefined,
  className: '',
  showDuration: true,
  showFavorite: true,
  favoriteItemType: 'track',
  favoriteItemId: undefined,
  favoriteMetadata: undefined,
};

export default TrackTile;
