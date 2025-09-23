import { useCallback, useEffect, useMemo } from 'react';
import { usePlayer } from '../player/PlayerContext';
import usePreviewAvailability, { PreviewAvailabilityStatus } from './usePreviewAvailability';

const DEFAULT_PREFETCH_COUNT = 5;

const filterTracksWithIds = (tracks) => {
  if (!Array.isArray(tracks)) return [];
  return tracks.filter((track) => track && track.spotify_id);
};

const usePreviewPlayback = (tracks, { resetKey, prefetchCount = DEFAULT_PREFETCH_COUNT } = {}) => {
  const player = usePlayer();
  const sanitizedTracks = useMemo(() => filterTracksWithIds(tracks), [tracks]);
  const { availability, getStatus, checkAvailability, prefetchBatch, reset } = usePreviewAvailability();

  useEffect(() => {
    if (resetKey === undefined) return;
    reset();
  }, [resetKey, reset]);

  useEffect(() => {
    if (!sanitizedTracks.length) return;
    const ids = sanitizedTracks.slice(0, prefetchCount).map((track) => track.spotify_id);
    if (ids.length) {
      prefetchBatch(ids);
    }
  }, [sanitizedTracks, prefetchBatch, prefetchCount]);

  const currentPreviewId = player?.currentTrack?.isPreview ? player.currentTrack.id : null;
  const isPreviewPlaying = Boolean(player?.currentTrack?.isPreview && player?.isPlaying);
  const isPreviewPaused = Boolean(player?.currentTrack?.isPreview && !player?.isPlaying);

  const prefetchTrack = useCallback(
    (track) => {
      if (!track?.spotify_id) return;
      prefetchBatch([track.spotify_id]);
    },
    [prefetchBatch],
  );

  const buildQueue = useCallback(() => {
    return sanitizedTracks
      .filter((track) => getStatus(track.spotify_id) === PreviewAvailabilityStatus.AVAILABLE)
      .map((track) => ({
        id: track.spotify_id,
        title: track.title,
        artists: track.artists || [],
        albumId: track.albumId,
        audioUrl: `/api/preview/${track.spotify_id}`,
        isPreview: true,
      }));
  }, [getStatus, sanitizedTracks]);

  const playTrack = useCallback(
    async (track) => {
      if (!player || !track?.spotify_id) return;

      if (player.currentTrack?.isPreview && player.currentTrack.id === track.spotify_id) {
        if (player.isPlaying) {
          player.pause();
        } else {
          player.play();
        }
        return;
      }

      let status = getStatus(track.spotify_id);
      if (status !== PreviewAvailabilityStatus.AVAILABLE) {
        status = await checkAvailability(track.spotify_id);
      }
      if (status !== PreviewAvailabilityStatus.AVAILABLE) {
        return;
      }

      const queue = buildQueue();
      const index = queue.findIndex((item) => item.id === track.spotify_id);
      if (index === -1 || queue.length === 0) {
        return;
      }
      player.playQueue(queue, index);
    },
    [buildQueue, checkAvailability, getStatus, player],
  );

  return {
    availability,
    playTrack,
    prefetchTrack,
    currentPreviewId,
    isPreviewPlaying,
    isPreviewPaused,
  };
};

export default usePreviewPlayback;
