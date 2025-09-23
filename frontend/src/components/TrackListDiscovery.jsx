import React, { useContext } from 'react';
import PropTypes from 'prop-types';
import { formatDuration } from '../utils/helpers';
import CompilationContext from '../compilation/CompilationContext.jsx';
import { PreviewAvailabilityStatus } from '../hooks/usePreviewAvailability';

const TrackListDiscovery = ({
  tracks,
  enablePlay,
  onPlayTrack,
  onPrefetchTrack,
  previewAvailability,
  activePreviewId,
  isPreviewPlaying,
  isPreviewPaused,
}) => {
  const compilation = useContext(CompilationContext);
  if (!tracks || tracks.length === 0) return null;

  return (
    <ul className="space-y-2">
      {tracks.map((track, index) => {
        const id = track.spotify_id || track.id || track.url || track.uri;
        const inCart = id ? compilation?.isInCompilation(id) : false;
        const availabilityEntry = previewAvailability?.[id];
        const availabilityStatus = availabilityEntry?.status || PreviewAvailabilityStatus.UNKNOWN;
        const isPreviewTrack = enablePlay && activePreviewId && activePreviewId === id;
        const previewLoading = availabilityStatus === PreviewAvailabilityStatus.LOADING;
        const previewUnavailable =
          availabilityStatus === PreviewAvailabilityStatus.UNAVAILABLE ||
          availabilityStatus === PreviewAvailabilityStatus.ERROR;

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

        const handlePreviewClick = (e) => {
          e.stopPropagation();
          if (!enablePlay || !onPlayTrack) return;
          onPlayTrack(track, index);
        };

        const handlePreviewPrefetch = () => {
          if (!enablePlay || !onPrefetchTrack) return;
          onPrefetchTrack(track, index);
        };

        let previewTitle;
        if (enablePlay) {
          if (previewLoading) previewTitle = 'Checking preview availability…';
          else if (previewUnavailable) previewTitle = 'Preview unavailable';
          else if (isPreviewTrack && isPreviewPlaying) previewTitle = 'Pause preview';
          else if (isPreviewTrack && isPreviewPaused) previewTitle = 'Resume preview';
          else previewTitle = 'Play 10-second preview';
        }

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
              {enablePlay && previewUnavailable && (
                <p className="text-xs text-slate-500 dark:text-gray-500 mt-1">Preview unavailable</p>
              )}
              {enablePlay && previewLoading && (
                <p className="text-xs text-slate-500 dark:text-gray-500 mt-1">Checking preview…</p>
              )}
            </div>
            <div className="flex items-center gap-3">
              {enablePlay && (
                <button
                  type="button"
                  onClick={handlePreviewClick}
                  onMouseEnter={handlePreviewPrefetch}
                  onFocus={handlePreviewPrefetch}
                  disabled={previewUnavailable}
                  className={`relative flex items-center justify-center w-10 h-10 rounded-full border-2 transition-transform ${
                    isPreviewTrack ? 'border-brand-500 dark:border-brandDark-400' : 'border-brand-200 dark:border-gray-600'
                  } ${
                    previewUnavailable
                      ? 'opacity-40 cursor-not-allowed'
                      : 'bg-white dark:bg-gray-700 hover:scale-105 shadow-sm'
                  }`}
                  title={previewTitle}
                >
                  <span
                    className={`preview-disc ${
                      isPreviewTrack && isPreviewPlaying
                        ? 'spin-slow'
                        : isPreviewTrack
                        ? 'preview-disc-active'
                        : ''
                    }`}
                    aria-hidden="true"
                  />
                  {isPreviewTrack && previewLoading && (
                    <span className="absolute inset-0 flex items-center justify-center text-xs text-brand-600 dark:text-brandDark-300">
                      …
                    </span>
                  )}
                </button>
              )}
              <button
                type="button"
                onClick={handleToggle}
                className={`px-2 py-1 rounded text-sm ${
                  inCart ? 'bg-brandError-600 text-white hover:bg-brandError-700' : 'bg-brand-600 text-white hover:bg-brand-700'
                }`}
                title={inCart ? 'Remove from compilation' : 'Add to compilation'}
              >
                {inCart ? 'Remove' : '+'}
              </button>
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
  enablePlay: PropTypes.bool,
  onPlayTrack: PropTypes.func,
  onPrefetchTrack: PropTypes.func,
  previewAvailability: PropTypes.objectOf(
    PropTypes.shape({
      status: PropTypes.string,
    }),
  ),
  activePreviewId: PropTypes.string,
  isPreviewPlaying: PropTypes.bool,
  isPreviewPaused: PropTypes.bool,
};

TrackListDiscovery.defaultProps = {
  tracks: [],
  enablePlay: false,
  onPlayTrack: null,
  onPrefetchTrack: null,
  previewAvailability: {},
  activePreviewId: null,
  isPreviewPlaying: false,
  isPreviewPaused: false,
};

export default TrackListDiscovery;
