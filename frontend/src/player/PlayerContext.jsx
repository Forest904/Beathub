import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import PropTypes from 'prop-types';

const PlayerContext = createContext(null);

export const PlayerProvider = ({ children, disabled }) => {
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

  const disabledValue = useMemo(
    () => ({
      queue: [],
      index: -1,
      isPlaying: false,
      currentTrack: null,
      playQueue: () => {},
      play: () => {},
      pause: () => {},
      toggle: () => {},
      next: () => {},
      prev: () => {},
      stop: () => {},
      seekTo: () => {},
      currentTime: 0,
      duration: 0,
      hasNext: false,
      hasPrev: false,
      volume: 1,
      setVolume: () => {},
      shuffleEnabled: false,
      repeatEnabled: false,
      toggleShuffle: () => {},
      toggleRepeat: () => {},
    }),
    [],
  );

  // Wire audio element events
  useEffect(() => {
    if (disabled) {
      return undefined;
    }
    const audio = audioRef.current;
    if (!audio) return undefined;
    const handleEnded = () => {
      if (repeatEnabled) return;
      if (shuffleEnabled && queue.length > 0) {
        if (queue.length === 1) return;
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
        setIsPlaying(false);
        setIndex(-1);
        setQueue([]);
      }
    };
    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleError = () => {
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
  }, [disabled, index, queue.length, shuffleEnabled, repeatEnabled]);

  // Time/Durations events
  useEffect(() => {
    if (disabled) {
      return undefined;
    }
    const audio = audioRef.current;
    if (!audio) return undefined;
    const handleTime = () => setCurrentTime(Number.isFinite(audio.currentTime) ? audio.currentTime : 0);
    const handleMeta = () => setDuration(Number.isFinite(audio.duration) ? audio.duration : 0);
    const handleEmptied = () => {
      setCurrentTime(0);
      setDuration(0);
    };
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
  }, [disabled]);

  // Update <audio> src when current track changes
  useEffect(() => {
    if (disabled) {
      return;
    }
    const audio = audioRef.current;
    if (!audio) return;
    if (currentTrack && currentTrack.audioUrl) {
      setCurrentTime(0);
      setDuration(0);
      audio.src = currentTrack.audioUrl;
      const playPromise = audio.play();
      if (playPromise && typeof playPromise.then === 'function') {
        playPromise.catch(() => {
          setIsPlaying(false);
        });
      }
    } else {
      audio.pause();
      audio.removeAttribute('src');
      try {
        audio.load();
      } catch (e) {
        /* no-op */
      }
      setCurrentTime(0);
      setDuration(0);
    }
  }, [disabled, currentTrack]);

  // Sync repeat and volume with audio element
  useEffect(() => {
    if (disabled) {
      return;
    }
    const audio = audioRef.current;
    if (!audio) return;
    audio.loop = !!repeatEnabled;
  }, [disabled, repeatEnabled]);

  useEffect(() => {
    if (disabled) {
      return;
    }
    const audio = audioRef.current;
    if (!audio) return;
    const v = Math.min(1, Math.max(0, Number(volume) || 0));
    audio.volume = v;
  }, [disabled, volume]);

  const playQueue = useCallback(
    (newQueue, startIndex = 0) => {
      if (disabled || !Array.isArray(newQueue) || newQueue.length === 0) return;
      setQueue(newQueue);
      setIndex(Math.max(0, Math.min(startIndex, newQueue.length - 1)));
    },
    [disabled],
  );

  const play = useCallback(() => {
    if (disabled) return;
    const audio = audioRef.current;
    if (!audio) return;
    audio.play();
  }, [disabled]);

  const pause = useCallback(() => {
    if (disabled) return;
    const audio = audioRef.current;
    if (!audio) return;
    audio.pause();
  }, [disabled]);

  const toggle = useCallback(() => {
    if (disabled) return;
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) audio.play();
    else audio.pause();
  }, [disabled]);

  const next = useCallback(() => {
    if (disabled) return;
    if (repeatEnabled) {
      const audio = audioRef.current;
      if (audio) {
        try {
          audio.currentTime = 0;
        } catch (_) {
          /* ignore */
        }
        try {
          audio.play();
        } catch (_) {
          /* ignore */
        }
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
  }, [disabled, index, queue.length, shuffleEnabled, repeatEnabled]);

  const prev = useCallback(() => {
    if (disabled) return;
    if (index > 0) setIndex((i) => i - 1);
  }, [disabled, index]);

  const stop = useCallback(() => {
    if (disabled) return;
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
    }
    setIsPlaying(false);
    setIndex(-1);
    setQueue([]);
    setCurrentTime(0);
    setDuration(0);
  }, [disabled]);

  const seekTo = useCallback(
    (timeSec) => {
      if (disabled) return;
      const audio = audioRef.current;
      if (!audio) return;
      const t = Math.max(
        0,
        Math.min(Number(timeSec) || 0, Number.isFinite(audio.duration) ? audio.duration : Infinity),
      );
      try {
        audio.currentTime = t;
      } catch (e) {
        /* ignore */
      }
    },
    [disabled],
  );

  const activeValue = useMemo(
    () => ({
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
      toggleShuffle: () =>
        setShuffleEnabled((s) => {
          const nextState = !s;
          if (nextState) setRepeatEnabled(false);
          return nextState;
        }),
      toggleRepeat: () =>
        setRepeatEnabled((r) => {
          const nextState = !r;
          if (nextState) setShuffleEnabled(false);
          return nextState;
        }),
    }),
    [
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
      volume,
      shuffleEnabled,
      repeatEnabled,
    ],
  );

  const value = disabled ? disabledValue : activeValue;

  return (
    <PlayerContext.Provider value={value}>
      {children}
      {!disabled && <audio ref={audioRef} hidden />}
    </PlayerContext.Provider>
  );
};

export const usePlayer = () => useContext(PlayerContext);

export default PlayerContext;

PlayerProvider.propTypes = {
  children: PropTypes.node.isRequired,
  disabled: PropTypes.bool,
};

PlayerProvider.defaultProps = {
  disabled: false,
};
