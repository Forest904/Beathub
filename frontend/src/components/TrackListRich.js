import React from 'react';
import PropTypes from 'prop-types';
import { formatDuration } from '../utils/helpers';

const BADGE_VARIANTS = {
  gray: 'bg-gray-700 text-gray-200',
  red: 'bg-red-700 text-white',
  blue: 'bg-blue-700 text-white',
  green: 'bg-green-700 text-white',
  yellow: 'bg-yellow-600 text-black',
};

const Badge = ({ children, color }) => (
  <span className={`px-2 py-0.5 rounded text-xs ${BADGE_VARIANTS[color] ?? BADGE_VARIANTS.gray}`}>{children}</span>
);

Badge.propTypes = {
  children: PropTypes.node.isRequired,
  color: PropTypes.oneOf(Object.keys(BADGE_VARIANTS)),
};

Badge.defaultProps = {
  color: 'gray',
};

const TrackListRich = ({ tracks }) => {
  if (!tracks || tracks.length === 0) {
    return null;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left text-gray-300">
            <th className="px-2 py-2">#</th>
            <th className="px-2 py-2">Title</th>
            <th className="px-2 py-2">Artists</th>
            <th className="px-2 py-2">Duration</th>
            <th className="px-2 py-2">Explicit</th>
            <th className="px-2 py-2">ISRC</th>
            <th className="px-2 py-2">Disc</th>
            <th className="px-2 py-2">Popularity</th>
          </tr>
        </thead>
        <tbody>
          {tracks.map((track, index) => (
            <tr key={track.spotify_id || index} className="border-t border-gray-700">
              <td className="px-2 py-2 text-gray-400">{track.track_number ?? index + 1}</td>
              <td className="px-2 py-2 text-white">
                <div className="flex items-center gap-2">
                  <span className="truncate max-w-[28ch]" title={track.title}>
                    {track.title}
                  </span>
                  {track.local_lyrics_path && <Badge color="green">Lyrics</Badge>}
                  {(track._missing || track.missing || track.file_missing || track.local_path === null || track.local_path === undefined) && (
                    <Badge color="red">Missing</Badge>
                  )}
                </div>
              </td>
              <td className="px-2 py-2 text-gray-300 truncate max-w-[32ch]" title={(track.artists || []).join(', ')}>
                {(track.artists || []).join(', ')}
              </td>
              <td className="px-2 py-2 text-gray-300">{formatDuration(track.duration_ms)}</td>
              <td className="px-2 py-2">{track.explicit ? <Badge color="red">E</Badge> : <span className="text-gray-500">N/A</span>}</td>
              <td className="px-2 py-2 text-gray-300 truncate max-w-[18ch]" title={track.isrc || ''}>
                {track.isrc || 'N/A'}
              </td>
              <td className="px-2 py-2 text-gray-300">
                {track.disc_number}
                {track.disc_count ? `/${track.disc_count}` : ''}
              </td>
              <td className="px-2 py-2 text-gray-300">{track.popularity ?? 'N/A'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

TrackListRich.propTypes = {
  tracks: PropTypes.arrayOf(
    PropTypes.shape({
      spotify_id: PropTypes.string,
      track_number: PropTypes.number,
      title: PropTypes.string.isRequired,
      artists: PropTypes.arrayOf(PropTypes.string),
      duration_ms: PropTypes.number,
      explicit: PropTypes.bool,
      isrc: PropTypes.string,
      disc_number: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
      disc_count: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
      popularity: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
      local_lyrics_path: PropTypes.string,
    }),
  ),
};

TrackListRich.defaultProps = {
  tracks: [],
};

export default TrackListRich;
