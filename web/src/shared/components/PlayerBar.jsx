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

const SvgIcon = ({ children, className = 'w-5 h-5' }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {children}
  </svg>
);

const PrevIcon = (props) => (
  <SvgIcon {...props}>
    <path d="M21 17.25 13.5 12 21 6.75v10.5Z" fill="currentColor" stroke="none" />
    <path d="M11.25 17.25 3.75 12l7.5-5.25v10.5Z" fill="currentColor" stroke="none" />
  </SvgIcon>
);

const NextIcon = (props) => (
  <SvgIcon {...props}>
    <path d="m3 17.25 7.5-5.25L3 6.75v10.5Z" fill="currentColor" stroke="none" />
    <path d="m12.75 17.25 7.5-5.25-7.5-5.25v10.5Z" fill="currentColor" stroke="none" />
  </SvgIcon>
);

const PlayIcon = (props) => (
  <SvgIcon {...props}>
    <path d="m8.25 5.25 9 6-9 6v-12Z" fill="currentColor" stroke="none" />
  </SvgIcon>
);

const PauseIcon = (props) => (
  <SvgIcon {...props}>
    <path d="M9 6.75v10.5M15 6.75v10.5" />
  </SvgIcon>
);

const ShuffleIcon = (props) => (
  <SvgIcon {...props}>
    <path d="M4.5 7.5h2.121a3 3 0 0 1 2.121.879l6.087 6.087A3 3 0 0 0 17.95 15H19.5m0-7.5h-1.55a3 3 0 0 0-2.121.879l-.879.879m0 5.25.879.879A3 3 0 0 0 17.95 16.5H19.5m-15 0h2.121a3 3 0 0 0 2.121-.879l1.409-1.409" />
    <path d="M16.5 6 19.5 9m-3 9 3-3" />
  </SvgIcon>
);

const RepeatIcon = (props) => (
  <SvgIcon {...props}>
    <path d="M7.5 7.5h8.25A3.75 3.75 0 0 1 19.5 11.25v.75" />
    <path d="M16.5 5.25 19.5 7.5 16.5 9.75" />
    <path d="M16.5 16.5H8.25A3.75 3.75 0 0 1 4.5 12.75v-.75" />
    <path d="M7.5 18.75 4.5 16.5 7.5 14.25" />
  </SvgIcon>
);

const VolumeIcon = (props) => (
  <SvgIcon {...props}>
    <path d="M4.5 9.75h2.25L11.25 6v12l-4.5-3.75H4.5z" fill="currentColor" stroke="none" />
    <path d="M16.5 8.25a3.75 3.75 0 0 1 0 7.5M18.75 6.75a6 6 0 0 1 0 10.5" />
  </SvgIcon>
);

const ChevronDownIcon = (props) => (
  <SvgIcon {...props}>
    <path d="M6 9l6 6 6-6" />
  </SvgIcon>
);

const ChevronUpIcon = (props) => (
  <SvgIcon {...props}>
    <path d="M6 15l6-6 6 6" />
  </SvgIcon>
);

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
              <IconButton label="Previous" disabled={!hasPrev} onClick={prev}>
                <PrevIcon />
              </IconButton>
              <button
                type="button"
                onClick={toggle}
                className="px-4 py-1 rounded bg-brand-600 hover:bg-brand-700 text-white dark:bg-brandDark-600 dark:hover:bg-brandDark-500"
                title={isPlaying ? 'Pause' : 'Play'}
              >
                {isPlaying ? <PauseIcon className="w-6 h-6" /> : <PlayIcon className="w-6 h-6" />}
              </button>
              <IconButton label="Next" disabled={!hasNext} onClick={next}>
                <NextIcon />
              </IconButton>
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
                <ShuffleIcon />
              </button>
              <button
                type="button"
                onClick={toggleRepeat}
                aria-pressed={repeatEnabled}
                className={`px-2 py-1 rounded hover:bg-slate-100 dark:hover:bg-gray-800 ${repeatEnabled ? 'text-brand-600 dark:text-brandDark-400 ring-2 ring-brand-600 dark:ring-brandDark-400 ring-offset-1 ring-offset-white dark:ring-offset-gray-900' : 'text-slate-600 dark:text-gray-300'}`}
                title={repeatEnabled ? 'Disable repeat' : 'Enable repeat'}
              >
                <RepeatIcon />
              </button>
            </div>

            <div className="flex items-center gap-2 ml-auto">
              <VolumeIcon className="w-5 h-5" />
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
                <ChevronDownIcon />
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
            <ChevronUpIcon />
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
