import React, { useContext } from 'react';
import PropTypes from 'prop-types';
import { formatDuration } from '../utils/formatting';
import CompilationContext from '../../features/compilations/context/CompilationContext.jsx';
import { useAuth } from '../hooks/useAuth';

const BADGE_VARIANTS = {
  gray: 'bg-slate-200 text-slate-700 dark:bg-gray-700 dark:text-gray-200',
  red: 'bg-brandError-600 text-white dark:bg-brandError-700',
  blue: 'bg-brand-600 text-white dark:bg-brandDark-700',
  green: 'bg-brandSuccess-600 text-white dark:bg-brandSuccess-700',
  yellow: 'bg-brandWarning-500 text-black dark:bg-brandWarning-600',
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

const TrackListRich = ({ tracks, compactForBurnPreview, showDiscHeaders, showExplicit, showIsrc, showDisc, showPopularity, onLyricsClick, enablePlay, onPlayTrack }) => {
  const compilation = useContext(CompilationContext);
  const { user } = useAuth();
  if (!tracks || tracks.length === 0) {
    return null;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left text-brand-800 dark:text-gray-300">
            <th className="px-2 py-2">#</th>
            {(!compactForBurnPreview && enablePlay) && <th className="px-2 py-2 w-12"></th>}
            <th className="px-2 py-2">Title</th>
            <th className="px-2 py-2">Artists</th>
            <th className="px-2 py-2">Duration</th>
            {(!compactForBurnPreview && showExplicit) && <th className="px-2 py-2">Explicit</th>}
            {(!compactForBurnPreview && showIsrc) && <th className="px-2 py-2">ISRC</th>}
            {showDisc && <th className="px-2 py-2">Disc</th>}
            {(!compactForBurnPreview && showPopularity) && <th className="px-2 py-2">Popularity</th>}
            {(!compactForBurnPreview && compilation?.compilationMode && user) && <th className="px-2 py-2">Compilation</th>}
          </tr>
        </thead>
        <tbody>
          {(() => {
            const useShowExplicit = !compactForBurnPreview && showExplicit;
            const useShowIsrc = !compactForBurnPreview && showIsrc;
            const useShowPopularity = !compactForBurnPreview && showPopularity;
            const useEnablePlay = !compactForBurnPreview && enablePlay;
            const useCompilationControls = !compactForBurnPreview && Boolean(compilation?.compilationMode) && Boolean(user);
            const colSpan = 4 + (useEnablePlay ? 1 : 0) + (useShowExplicit ? 1 : 0) + (useShowIsrc ? 1 : 0) + (showDisc ? 1 : 0) + (useShowPopularity ? 1 : 0) + (useCompilationControls ? 1 : 0);
            let lastDisc = null;
            const rows = [];
            tracks.forEach((track, index) => {
              const discNum = Number(track?.disc_number ?? 1);
              const isMissing = Boolean(
                track._missing || track.missing || track.file_missing || track.local_path === null || track.local_path === undefined,
              );
              if (showDiscHeaders && lastDisc !== discNum) {
                rows.push(
                  <tr key={`disc-${discNum}`} className="border-t border-brand-100 dark:border-gray-700 bg-brand-50 dark:bg-gray-800/70">
                    <td className="px-2 py-2 text-sm font-semibold text-brand-700 dark:text-brandDark-300" colSpan={colSpan}>
                      Disc {discNum}
                    </td>
                  </tr>,
                );
                lastDisc = discNum;
              }

              rows.push(
                <tr key={track.spotify_id || `${discNum}-${index}`} className="border-t border-slate-200 dark:border-gray-700">
                  <td className="px-2 py-2 text-slate-600 dark:text-gray-400">{track.track_number ?? index + 1}</td>
                  {useEnablePlay && (
                    <td className="px-2 py-2">
                      <button
                        type="button"
                        disabled={isMissing || typeof onPlayTrack !== 'function'}
                        onClick={(e) => { e.stopPropagation(); if (typeof onPlayTrack === 'function') onPlayTrack(track, index); }}
                        className={`px-2 py-1 rounded ${isMissing ? 'bg-slate-100 text-slate-400 cursor-not-allowed dark:bg-gray-800 dark:text-gray-600' : 'bg-brand-600 text-white hover:bg-brand-700 dark:bg-brandDark-600 dark:hover:bg-brandDark-500'}`}
                        title={isMissing ? 'Audio missing' : 'Play'}
                      >
                        ▶
                      </button>
                    </td>
                  )}
                  <td className="px-2 py-2 text-slate-900 dark:text-white">
                    <div className="flex items-center gap-2">
                    <span
                      className={`truncate max-w-[28ch] ${compactForBurnPreview && isMissing ? 'text-brandError-600 dark:text-brandError-400' : ''}`}
                      title={track.title}
                    >
                      {track.title}
                    </span>
                      {(() => {
                        const hasLyrics = Boolean(track.local_lyrics_path || track.has_embedded_lyrics);
                        const lyricsKnown = ('local_lyrics_path' in track) || (typeof track.has_embedded_lyrics !== 'undefined');
                        if (!lyricsKnown) return null;
                        const handleClick = (e) => {
                          e.stopPropagation();
                          if (typeof onLyricsClick === 'function') onLyricsClick(track);
                        };
                        if (hasLyrics) {
                          return (
                            <button
                              type="button"
                              onClick={handleClick}
                              className="focus:outline-none cursor-pointer"
                              title="Show lyrics"
                            >
                              <Badge color="green">Lyrics</Badge>
                            </button>
                          );
                        }
                        return (
                          <button
                            type="button"
                            onClick={handleClick}
                            className="focus:outline-none cursor-pointer"
                            title="Lyrics not found — open panel"
                          >
                            <Badge color="red">Lyrics</Badge>
                          </button>
                        );
                      })()}
                      {!compactForBurnPreview && isMissing && <Badge color="red">Missing</Badge>}
                    </div>
                  </td>
                  <td className="px-2 py-2 text-slate-600 dark:text-gray-300 truncate max-w-[32ch]" title={(track.artists || []).join(', ')}>
                    {(track.artists || []).join(', ')}
                  </td>
                  <td className="px-2 py-2 text-slate-600 dark:text-gray-300">{formatDuration(track.duration_ms)}</td>
                  {useShowExplicit && (
                    <td className="px-2 py-2">{track.explicit ? <Badge color="red">E</Badge> : <span className="text-slate-500 dark:text-gray-500">N/A</span>}</td>
                  )}
                  {useShowIsrc && (
                    <td className="px-2 py-2 text-slate-600 dark:text-gray-300 truncate max-w-[18ch]" title={track.isrc || ''}>
                      {track.isrc || 'N/A'}
                    </td>
                  )}
                  {showDisc && (
                    <td className="px-2 py-2 text-slate-600 dark:text-gray-300">
                      {track.disc_number}
                      {track.disc_count ? `/${track.disc_count}` : ''}
                    </td>
                  )}
                  {useShowPopularity && (
                    <td className="px-2 py-2 text-slate-600 dark:text-gray-300">{track.popularity ?? 'N/A'}</td>
                  )}
                  {useCompilationControls && (
                    <td className="px-2 py-2">
                      {(() => {
                        const id = track.spotify_id || track.id || track.url || track.uri;
                        const inCart = id ? compilation.isInCompilation(id) : false;
                        const handleToggle = (e) => {
                          e.stopPropagation();
                          if (!id) return;
                          if (inCart) {
                            compilation.remove(id);
                          } else {
                            const item = {
                              spotify_id: track.spotify_id || id,
                              title: track.title,
                              artists: track.artists || [],
                              duration_ms: track.duration_ms,
                              albumId: track.albumId,
                            };
                            compilation.add(item);
                          }
                        };
                        return (
                          <button
                            type="button"
                            onClick={handleToggle}
                            className={`px-2 py-1 rounded text-sm ${inCart ? 'bg-brandError-600 text-white hover:bg-brandError-700' : 'bg-brand-600 text-white hover:bg-brand-700'}`}
                            title={inCart ? 'Remove from compilation' : 'Add to compilation'}
                          >
                            {inCart ? 'Remove' : 'Add'}
                          </button>
                        );
                      })()}
                    </td>
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
      albumId: PropTypes.string,
    }),
  ),
  compactForBurnPreview: PropTypes.bool,
  showDiscHeaders: PropTypes.bool,
  showExplicit: PropTypes.bool,
  showIsrc: PropTypes.bool,
  showDisc: PropTypes.bool,
  showPopularity: PropTypes.bool,
  onLyricsClick: PropTypes.func,
  enablePlay: PropTypes.bool,
  onPlayTrack: PropTypes.func,
};

TrackListRich.defaultProps = {
  tracks: [],
  compactForBurnPreview: false,
  showDiscHeaders: false,
  showExplicit: true,
  showIsrc: true,
  showDisc: true,
  showPopularity: true,
  onLyricsClick: undefined,
  enablePlay: false,
  onPlayTrack: undefined,
};

export default TrackListRich;
