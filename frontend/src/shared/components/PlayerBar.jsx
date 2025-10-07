import React, { useEffect, useMemo, useState } from 'react';
import { usePlayer } from '../../player/PlayerContext';
import LyricsPanel from '../../features/downloads/components/LyricsPanel.jsx';
import { API_BASE_URL } from '../../api/client';

const formatTime = (seconds) => {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00';
  const total = Math.floor(seconds);
  const minutes = Math.floor(total / 60);
  const secs = total % 60;
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
};

const resolveApiBaseUrl = () => {
  if (API_BASE_URL) return API_BASE_URL;
  if (typeof window !== 'undefined') {
    return window.location.origin.replace(/\/$/, '');
  }
  return '';
};

const IconButton = ({ label, disabled, onClick, children }) => (
  <button
    type="button"
    onClick={onClick}
    disabled={disabled}
    className={`px-3 py-1 rounded transition-colors ${
      disabled
        ? 'bg-slate-200 text-slate-400 cursor-not-allowed dark:bg-gray-700 dark:text-gray-500'
        : 'bg-slate-200 hover:bg-slate-300 text-slate-700 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-200'
    }`}
    title={label}
    aria-label={label}
  >
    {children}
  </button>
);

const PlayerBar = () => {
  const {
    currentTrack,
    isPlaying,
    toggle,
    next,
    prev,
    hasNext,
    hasPrev,
    currentTime,
    duration,
    seekTo,
    shuffleEnabled,
    repeatEnabled,
    toggleShuffle,
    toggleRepeat,
    volume,
    setVolume,
  } = usePlayer() || {};
  const [lyricsVisible, setLyricsVisible] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const onKey = (event) => {
      if (event.key === 'Escape') {
        setCollapsed(true);
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    if (currentTrack) {
      setCollapsed(false);
    }
  }, [currentTrack]);

  const apiBaseUrl = useMemo(() => resolveApiBaseUrl(), []);

  if (!currentTrack) return null;

  const title = currentTrack.title || 'Unknown Title';
  const artistsArray = Array.isArray(currentTrack.artists) ? currentTrack.artists : (currentTrack.artist ? [currentTrack.artist] : []);
  const artists = artistsArray.join(', ');
  const albumId = currentTrack?.albumId ?? null;
  const canOpenLyrics = albumId !== null && title.trim().length > 0;

  const handleSeek = (event) => {
    const nextValue = parseFloat(event.target.value);
    if (Number.isFinite(nextValue) && seekTo) {
      seekTo(nextValue);
    }
  };

  const handleVolumeChange = (event) => {
    const nextValue = parseInt(event.target.value, 10);
    if (!Number.isFinite(nextValue) || !setVolume) return;
    setVolume(Math.min(1, Math.max(0, nextValue / 100)));
  };

  return (
    <div
      id="player-bar-root"
      className="fixed bottom-0 left-0 right-0 z-40"
      onClick={(e) => e.stopPropagation()}
      onMouseDown={(e) => e.stopPropagation()}
    >
      <div className={`bg-white/95 dark:bg-gray-900/95 border-t border-slate-200 dark:border-gray-800 shadow-lg transform transition-transform duration-200 ${collapsed ? 'translate-y-full' : 'translate-y-0'}`}>
        <div className="container mx-auto px-4 py-2 flex flex-col gap-2">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <IconButton label="Previous" disabled={!hasPrev} onClick={prev}>?</IconButton>
              <button
                type="button"
                onClick={toggle}
                className="px-4 py-1 rounded bg-brand-600 hover:bg-brand-700 text-white dark:bg-brandDark-600 dark:hover:bg-brandDark-500"
                title={isPlaying ? 'Pause' : 'Play'}
              >
                {isPlaying ? '?' : '??'}
              </button>
              <IconButton label="Next" disabled={!hasNext} onClick={next}>?</IconButton>
            </div>

            <div className="flex-1 flex items-center gap-3">
              <span className="text-xs tabular-nums text-slate-700 dark:text-gray-300 min-w-[36px] text-right">{formatTime(currentTime)}</span>
              <input
                type="range"
                min={0}
                max={Math.max(duration || 0, 0)}
                step={0.1}
                value={Number.isFinite(currentTime) ? currentTime : 0}
                onChange={handleSeek}
                className="w-full h-1 rounded bg-slate-200 dark:bg-gray-700 accent-brand-600"
              />
              <span className="text-xs tabular-nums text-slate-700 dark:text-gray-300 min-w-[36px]">{formatTime(duration)}</span>
            </div>

            <div className="shrink-0 flex items-center gap-2">
              <button
                type="button"
                onClick={() => setLyricsVisible(true)}
                disabled={!canOpenLyrics}
                className={`px-2 py-0.5 rounded text-xs ${canOpenLyrics ? 'bg-brand-600 text-white hover:bg-brand-700 dark:bg-brandDark-600 dark:hover:bg-brandDark-500' : 'bg-slate-200 text-slate-400 dark:bg-gray-700 dark:text-gray-500 cursor-not-allowed'}`}
                title={canOpenLyrics ? 'Show lyrics' : 'Lyrics unavailable'}
              >
                Lyrics
              </button>
              <button
                type="button"
                onClick={toggleShuffle}
                aria-pressed={shuffleEnabled}
                className={`px-2 py-1 rounded hover:bg-slate-100 dark:hover:bg-gray-800 ${shuffleEnabled ? 'text-brand-600 dark:text-brandDark-400 ring-2 ring-brand-600 dark:ring-brandDark-400 ring-offset-1 ring-offset-white dark:ring-offset-gray-900' : 'text-slate-600 dark:text-gray-300'}`}
                title={shuffleEnabled ? 'Disable shuffle' : 'Enable shuffle'}
              >
                ??
              </button>
              <button
                type="button"
                onClick={toggleRepeat}
                aria-pressed={repeatEnabled}
                className={`px-2 py-1 rounded hover:bg-slate-100 dark:hover:bg-gray-800 ${repeatEnabled ? 'text-brand-600 dark:text-brandDark-400 ring-2 ring-brand-600 dark:ring-brandDark-400 ring-offset-1 ring-offset-white dark:ring-offset-gray-900' : 'text-slate-600 dark:text-gray-300'}`}
                title={repeatEnabled ? 'Disable repeat' : 'Enable repeat'}
              >
                ??
              </button>
            </div>

            <div className="flex items-center gap-2 ml-auto">
              <span className="text-lg" title="Volume">??</span>
              <input
                type="range"
                min={0}
                max={100}
                step={1}
                value={Math.round((Number.isFinite(volume) ? volume : 1) * 100)}
                onChange={handleVolumeChange}
                className="w-28 h-1 rounded bg-slate-200 dark:bg-gray-700 accent-brand-600"
              />
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setCollapsed(true); }}
                className="inline-flex items-center justify-center rounded-md border border-slate-300 p-2 text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
                title="Hide player"
                aria-label="Hide player"
              >
                <span className="text-lg">??</span>
              </button>
            </div>
          </div>

          <div className="min-w-0 text-center px-1">
            <div className="text-sm font-semibold text-slate-900 dark:text-white truncate" title={title}>{title}</div>
            {artists && <div className="text-xs text-slate-600 dark:text-gray-400 truncate" title={artists}>{artists}</div>}
          </div>
        </div>
      </div>
      {collapsed && (
        <div className="absolute bottom-2 right-4">
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); setCollapsed(false); }}
            className="inline-flex items-center justify-center rounded-full bg-brand-600 text-white hover:bg-brand-700 dark:bg-brandDark-600 dark:hover:bg-brandDark-500 shadow p-2"
            title="Show player"
            aria-label="Show player"
          >
            ??
          </button>
        </div>
      )}
      <LyricsPanel
        visible={lyricsVisible}
        onClose={() => setLyricsVisible(false)}
        baseUrl={apiBaseUrl}
        albumId={albumId}
        track={{ title, artists: artistsArray }}
      />
    </div>
  );
};

export default PlayerBar;
