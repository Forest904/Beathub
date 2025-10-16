import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

const PlayerContext = createContext(null);

export const PlayerProvider = ({ children }) => {
  const audioRef = useRef(null);
  const [queue, setQueue] = useState([]);
  const [index, setIndex] = useState(-1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [shuffleEnabled, setShuffleEnabled] = useState(false);
  const [repeatEnabled, setRepeatEnabled] = useState(false);
  const [volume, setVolume] = useState(1);

  const currentTrack = index >= 0 && index < queue.length ? queue[index] : null;

  // Wire audio element events
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return undefined;
    const handleEnded = () => {
      // Repeat handled by audio.loop; if enabled, ended won't fire
      if (repeatEnabled) return;
      if (shuffleEnabled && queue.length > 0) {
        if (queue.length === 1) return; // nothing to advance to
        let nextIdx = index;
        while (nextIdx === index) {
          nextIdx = Math.floor(Math.random() * queue.length);
        }
        setIndex(nextIdx);
        return;
      }
      if (index + 1 < queue.length) {
        setIndex((i) => i + 1);
      } else {
        // End of queue
        setIsPlaying(false);
        setIndex(-1);
        setQueue([]);
      }
    };
    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleError = () => {
      // Skip to next on error if possible
      if (index + 1 < queue.length) {
        setIndex((i) => i + 1);
      } else {
        setIsPlaying(false);
      }
    };
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('error', handleError);
    return () => {
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('error', handleError);
    };
  }, [index, queue.length, shuffleEnabled, repeatEnabled]);

  // Time/Durations events
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return undefined;
    const handleTime = () => setCurrentTime(isFinite(audio.currentTime) ? audio.currentTime : 0);
    const handleMeta = () => setDuration(isFinite(audio.duration) ? audio.duration : 0);
    const handleEmptied = () => { setCurrentTime(0); setDuration(0); };
    audio.addEventListener('timeupdate', handleTime);
    audio.addEventListener('loadedmetadata', handleMeta);
    audio.addEventListener('durationchange', handleMeta);
    audio.addEventListener('emptied', handleEmptied);
    return () => {
      audio.removeEventListener('timeupdate', handleTime);
      audio.removeEventListener('loadedmetadata', handleMeta);
      audio.removeEventListener('durationchange', handleMeta);
      audio.removeEventListener('emptied', handleEmptied);
    };
  }, []);

  // Update <audio> src when current track changes
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (currentTrack && currentTrack.audioUrl) {
      setCurrentTime(0);
      setDuration(0);
      audio.src = currentTrack.audioUrl;
      const playPromise = audio.play();
      if (playPromise && typeof playPromise.then === 'function') {
        playPromise.catch(() => {
          // Autoplay might be prevented; keep state consistent
          setIsPlaying(false);
        });
      }
    } else {
      audio.pause();
      audio.removeAttribute('src');
      try { audio.load(); } catch (e) { /* no-op */ }
      setCurrentTime(0);
      setDuration(0);
    }
  }, [currentTrack]);

  // Sync repeat and volume with audio element
  useEffect(() => {
    const audio = audioRef.current; if (!audio) return;
    audio.loop = !!repeatEnabled;
  }, [repeatEnabled]);

  useEffect(() => {
    const audio = audioRef.current; if (!audio) return;
    const v = Math.min(1, Math.max(0, Number(volume) || 0));
    audio.volume = v;
  }, [volume]);

  const playQueue = useCallback((newQueue, startIndex = 0) => {
    if (!Array.isArray(newQueue) || newQueue.length === 0) return;
    setQueue(newQueue);
    setIndex(Math.max(0, Math.min(startIndex, newQueue.length - 1)));
  }, []);

  const play = useCallback(() => {
    const audio = audioRef.current; if (!audio) return;
    audio.play();
  }, []);

  const pause = useCallback(() => {
    const audio = audioRef.current; if (!audio) return;
    audio.pause();
  }, []);

  const toggle = useCallback(() => {
    const audio = audioRef.current; if (!audio) return;
    if (audio.paused) audio.play(); else audio.pause();
  }, []);

  const next = useCallback(() => {
    // When repeat is enabled, forward should restart current song
    if (repeatEnabled) {
      const audio = audioRef.current;
      if (audio) {
        try { audio.currentTime = 0; } catch (_) { /* ignore */ }
        try { audio.play(); } catch (_) { /* ignore */ }
      }
      return;
    }
    if (shuffleEnabled && queue.length > 0) {
      if (queue.length === 1) return;
      let nextIdx = index;
      while (nextIdx === index) {
        nextIdx = Math.floor(Math.random() * queue.length);
      }
      setIndex(nextIdx);
      return;
    }
    if (index + 1 < queue.length) setIndex((i) => i + 1);
  }, [index, queue.length, shuffleEnabled, repeatEnabled]);

  const prev = useCallback(() => {
    if (index > 0) setIndex((i) => i - 1);
  }, [index]);

  const stop = useCallback(() => {
    const audio = audioRef.current; if (audio) { audio.pause(); }
    setIsPlaying(false);
    setIndex(-1);
    setQueue([]);
    setCurrentTime(0);
    setDuration(0);
  }, []);

  const seekTo = useCallback((timeSec) => {
    const audio = audioRef.current; if (!audio) return;
    const t = Math.max(0, Math.min(Number(timeSec) || 0, Number.isFinite(audio.duration) ? audio.duration : Infinity));
    try { audio.currentTime = t; } catch (e) { /* ignore */ }
  }, []);

  const value = useMemo(() => ({
    queue,
    index,
    isPlaying,
    currentTrack,
    playQueue,
    play,
    pause,
    toggle,
    next,
    prev,
    stop,
    seekTo,
    currentTime,
    duration,
    hasNext: index + 1 < queue.length,
    hasPrev: index > 0,
    volume,
    setVolume,
    shuffleEnabled,
    repeatEnabled,
    toggleShuffle: () => setShuffleEnabled((s) => { const ns = !s; if (ns) setRepeatEnabled(false); return ns; }),
    toggleRepeat: () => setRepeatEnabled((r) => { const nr = !r; if (nr) setShuffleEnabled(false); return nr; }),
  }), [queue, index, isPlaying, currentTrack, playQueue, play, pause, toggle, next, prev, stop, seekTo, currentTime, duration, volume, shuffleEnabled, repeatEnabled]);

  return (
    <PlayerContext.Provider value={value}>
      {children}
      {/* Hidden audio element for playback */}
      <audio ref={audioRef} hidden />
    </PlayerContext.Provider>
  );
};

export const usePlayer = () => useContext(PlayerContext);

export default PlayerContext;
