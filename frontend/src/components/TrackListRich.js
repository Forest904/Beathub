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

const TrackListRich = ({ tracks, compactForBurnPreview, showDiscHeaders, showExplicit, showIsrc, showDisc, showPopularity }) => {
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
            {(!compactForBurnPreview && showExplicit) && <th className="px-2 py-2">Explicit</th>}
            {(!compactForBurnPreview && showIsrc) && <th className="px-2 py-2">ISRC</th>}
            {showDisc && <th className="px-2 py-2">Disc</th>}
            {(!compactForBurnPreview && showPopularity) && <th className="px-2 py-2">Popularity</th>}
          </tr>
        </thead>
        <tbody>
          {(() => {
            const useShowExplicit = !compactForBurnPreview && showExplicit;
            const useShowIsrc = !compactForBurnPreview && showIsrc;
            const useShowPopularity = !compactForBurnPreview && showPopularity;
            const colSpan = 4 + (useShowExplicit ? 1 : 0) + (useShowIsrc ? 1 : 0) + (showDisc ? 1 : 0) + (useShowPopularity ? 1 : 0);
            let lastDisc = null;
            const rows = [];
            tracks.forEach((track, index) => {
              const discNum = Number(track?.disc_number ?? 1);
              const isMissing = Boolean(
                track._missing || track.missing || track.file_missing || track.local_path === null || track.local_path === undefined,
              );
              if (showDiscHeaders && lastDisc !== discNum) {
                rows.push(
                  <tr key={`disc-${discNum}`} className="border-t border-gray-700 bg-gray-800/70">
                    <td className="px-2 py-2 text-sm font-semibold text-sky-300" colSpan={colSpan}>
                      Disc {discNum}
                    </td>
                  </tr>,
                );
                lastDisc = discNum;
              }

              rows.push(
                <tr key={track.spotify_id || `${discNum}-${index}`} className="border-t border-gray-700">
                  <td className="px-2 py-2 text-gray-400">{track.track_number ?? index + 1}</td>
                  <td className="px-2 py-2 text-white">
                    <div className="flex items-center gap-2">
                    <span
                      className={`truncate max-w-[28ch] ${compactForBurnPreview && isMissing ? 'text-red-400' : ''}`}
                      title={track.title}
                    >
                      {track.title}
                    </span>
                      {(() => {
                        const hasLyrics = Boolean(track.local_lyrics_path || track.has_embedded_lyrics);
                        const lyricsKnown = ('local_lyrics_path' in track) || (typeof track.has_embedded_lyrics !== 'undefined');
                        return lyricsKnown ? (
                          <Badge color={hasLyrics ? 'green' : 'red'}>Lyrics</Badge>
                        ) : null;
                      })()}
                      {!compactForBurnPreview && isMissing && <Badge color="red">Missing</Badge>}
                    </div>
                  </td>
                  <td className="px-2 py-2 text-gray-300 truncate max-w-[32ch]" title={(track.artists || []).join(', ')}>
                    {(track.artists || []).join(', ')}
                  </td>
                  <td className="px-2 py-2 text-gray-300">{formatDuration(track.duration_ms)}</td>
                  {useShowExplicit && (
                    <td className="px-2 py-2">{track.explicit ? <Badge color="red">E</Badge> : <span className="text-gray-500">N/A</span>}</td>
                  )}
                  {useShowIsrc && (
                    <td className="px-2 py-2 text-gray-300 truncate max-w-[18ch]" title={track.isrc || ''}>
                      {track.isrc || 'N/A'}
                    </td>
                  )}
                  {showDisc && (
                    <td className="px-2 py-2 text-gray-300">
                      {track.disc_number}
                      {track.disc_count ? `/${track.disc_count}` : ''}
                    </td>
                  )}
                  {useShowPopularity && (
                    <td className="px-2 py-2 text-gray-300">{track.popularity ?? 'N/A'}</td>
                  )}
                </tr>,
              );
            });
            return rows;
          })()}
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
  compactForBurnPreview: PropTypes.bool,
  showDiscHeaders: PropTypes.bool,
  showExplicit: PropTypes.bool,
  showIsrc: PropTypes.bool,
  showDisc: PropTypes.bool,
  showPopularity: PropTypes.bool,
};

TrackListRich.defaultProps = {
  tracks: [],
  compactForBurnPreview: false,
  showDiscHeaders: false,
  showExplicit: true,
  showIsrc: true,
  showDisc: true,
  showPopularity: true,
};

export default TrackListRich;
