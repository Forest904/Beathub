import React, { useEffect, useState } from 'react';
import { usePlayer } from '../player/PlayerContext';
import LyricsPanel from './LyricsPanel';

const formatTime = (s) => {
  if (!Number.isFinite(s) || s < 0) return '0:00';
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
};

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
  const isPreviewTrack = Boolean(currentTrack?.isPreview);
  const [lyricsVisible, setLyricsVisible] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  // Hide player on ESC
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') setCollapsed(true);
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  if (!currentTrack) return null;

  const title = currentTrack.title || 'Unknown Title';
  const artists = Array.isArray(currentTrack.artists) ? currentTrack.artists.join(', ') : (currentTrack.artist || '');
  const apiBaseUrl = process.env.NODE_ENV === 'production' ? window.location.origin : 'http://127.0.0.1:5000';
  const canOpenLyrics = Boolean(currentTrack?.albumId && title);

  return (
    <div
      id="player-bar-root"
      className="fixed bottom-0 left-0 right-0 z-40"
      onClick={(e) => e.stopPropagation()}
      onMouseDown={(e) => e.stopPropagation()}
    >
      <div className={`bg-white/95 dark:bg-gray-900/95 border-t border-slate-200 dark:border-gray-800 shadow-lg transform transition-transform duration-200 ${collapsed ? 'translate-y-full' : 'translate-y-0'}`}>
        <div className="container mx-auto px-4 py-2 flex flex-col gap-2">
        {/* Row 1: Controls (left), Seekbar (center), Actions (right), Volume (far right) */}
        <div className="flex items-center gap-4">
          {/* Controls */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={prev}
              disabled={!hasPrev}
              className="px-3 py-1 rounded bg-slate-200 disabled:opacity-50 hover:bg-slate-300 text-slate-700 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-200"
              title="Previous"
            >
              ⏮
            </button>
            <button
              type="button"
              onClick={toggle}
              className="px-4 py-1 rounded bg-brand-600 hover:bg-brand-700 text-white dark:bg-brandDark-600 dark:hover:bg-brandDark-500"
              title={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? '⏸' : '▶'}
            </button>
            <button
              type="button"
              onClick={next}
              disabled={!hasNext}
              className="px-3 py-1 rounded bg-slate-200 disabled:opacity-50 hover:bg-slate-300 text-slate-700 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-200"
              title="Next"
            >
              ⏭
            </button>
          </div>
          {/* Seek bar */}
          <div className="flex-1 flex items-center gap-3">
            <span className="text-xs tabular-nums text-slate-700 dark:text-gray-300 min-w-[36px] text-right">{formatTime(currentTime)}</span>
            <input
              type="range"
              min={0}
              max={Math.max(duration || 0, 0)}
              step="0.1"
              value={Number.isFinite(currentTime) ? currentTime : 0}
              onChange={(e) => seekTo(parseFloat(e.target.value))}
              className="w-full h-1 rounded bg-slate-200 dark:bg-gray-700 accent-brand-600"
            />
            <span className="text-xs tabular-nums text-slate-700 dark:text-gray-300 min-w-[36px]">{formatTime(duration)}</span>
          </div>
          {/* Actions to the right of seekbar: Lyrics, Shuffle, Repeat */}
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
              className={`px-2 py-1 rounded hover:bg-slate-100 dark:hover:bg-gray-800 ${
                shuffleEnabled
                  ? 'text-brand-600 dark:text-brandDark-400 ring-2 ring-brand-600 dark:ring-brandDark-400 ring-offset-1 ring-offset-white dark:ring-offset-gray-900'
                  : (repeatEnabled ? 'text-slate-400 dark:text-gray-500' : 'text-slate-600 dark:text-gray-300')
              }`}
              title={shuffleEnabled ? 'Disable shuffle' : 'Enable shuffle'}
            >
              🔀
            </button>
            <button
              type="button"
              onClick={toggleRepeat}
              aria-pressed={repeatEnabled}
              className={`px-2 py-1 rounded hover:bg-slate-100 dark:hover:bg-gray-800 ${
                repeatEnabled
                  ? 'text-brand-600 dark:text-brandDark-400 ring-2 ring-brand-600 dark:ring-brandDark-400 ring-offset-1 ring-offset-white dark:ring-offset-gray-900'
                  : (shuffleEnabled ? 'text-slate-400 dark:text-gray-500' : 'text-slate-600 dark:text-gray-300')
              }`}
              title={repeatEnabled ? 'Disable repeat' : 'Enable repeat'}
            >
              🔁
            </button>
          </div>

          {/* Volume control (far right) */}
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-lg" title="Volume">🔊</span>
            <input
              type="range"
              min={0}
              max={100}
              step={1}
              value={Math.round((Number.isFinite(volume) ? volume : 1) * 100)}
              onChange={(e) => setVolume(Math.min(1, Math.max(0, (parseInt(e.target.value, 10) || 0) / 100)))}
              className="w-28 h-1 rounded bg-slate-200 dark:bg-gray-700 accent-brand-600"
            />
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); setCollapsed(true); }}
              className="px-2 py-1 rounded hover:bg-slate-100 dark:hover:bg-gray-800 text-slate-600 dark:text-gray-300"
              title="Hide player"
            >
              ⌄
            </button>
          </div>
        </div>
        {/* Row 2: Track info below seek bar */}
        <div className="min-w-0 text-center px-1">
          <div className="text-sm font-semibold text-slate-900 dark:text-white truncate" title={title}>{title}</div>
          {artists && <div className="text-xs text-slate-600 dark:text-gray-400 truncate" title={artists}>{artists}</div>}
          {isPreviewTrack && (
            <div className="mt-1 flex items-center justify-center">
              <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-brand-100 text-brand-700 text-xs font-semibold dark:bg-brandDark-700 dark:text-brandDark-200">
                Preview
              </span>
            </div>
          )}
        </div>
        </div>
      </div>
      {/* Show handle when collapsed */}
      {collapsed && (
        <div className="absolute bottom-2 right-4">
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); setCollapsed(false); }}
            className="px-3 py-1 rounded bg-brand-600 text-white hover:bg-brand-700 dark:bg-brandDark-600 dark:hover:bg-brandDark-500 shadow"
            title="Show player"
          >
            ⌃
          </button>
        </div>
      )}
      <LyricsPanel
        visible={lyricsVisible}
        onClose={() => setLyricsVisible(false)}
        baseUrl={apiBaseUrl}
        albumId={currentTrack?.albumId || null}
        track={{ title, artists: Array.isArray(currentTrack.artists) ? currentTrack.artists : (currentTrack.artist ? [currentTrack.artist] : []) }}
      />
    </div>
  );
};

export default PlayerBar;
