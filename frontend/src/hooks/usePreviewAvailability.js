import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';

export const PreviewAvailabilityStatus = Object.freeze({
  UNKNOWN: 'unknown',
  LOADING: 'loading',
  AVAILABLE: 'available',
  UNAVAILABLE: 'unavailable',
  ERROR: 'error',
});

const mergeStatus = (prevEntry, patch) => ({
  ...(prevEntry || {}),
  ...patch,
});

const usePreviewAvailability = () => {
  const [availability, setAvailability] = useState({});
  const inflightRef = useRef(new Map());
  const availabilityRef = useRef(availability);

  useEffect(() => {
    availabilityRef.current = availability;
  }, [availability]);

  const updateEntry = useCallback((trackId, patch) => {
    availabilityRef.current = {
      ...availabilityRef.current,
      [trackId]: mergeStatus(availabilityRef.current[trackId], patch),
    };
    setAvailability((prev) => ({
      ...prev,
      [trackId]: mergeStatus(prev[trackId], patch),
    }));
  }, []);

  const reset = useCallback(() => {
    inflightRef.current.clear();
    availabilityRef.current = {};
    setAvailability({});
  }, []);

  const getStatus = useCallback((trackId) => {
    if (!trackId) return PreviewAvailabilityStatus.UNKNOWN;
    return availabilityRef.current[trackId]?.status || PreviewAvailabilityStatus.UNKNOWN;
  }, []);

  const checkAvailability = useCallback(async (trackId) => {
    if (!trackId) {
      return PreviewAvailabilityStatus.UNKNOWN;
    }

    const existing = availabilityRef.current[trackId];
    if (existing && existing.status === PreviewAvailabilityStatus.AVAILABLE) {
      return PreviewAvailabilityStatus.AVAILABLE;
    }

    if (inflightRef.current.has(trackId)) {
      return inflightRef.current.get(trackId);
    }

    updateEntry(trackId, { status: PreviewAvailabilityStatus.LOADING });

    const request = axios
      .head(`/api/preview/${trackId}`)
      .then((response) => {
        const contentType = response?.headers?.['content-type'] || response?.headers?.['Content-Type'] || null;
        updateEntry(trackId, {
          status: PreviewAvailabilityStatus.AVAILABLE,
          contentType,
        });
        return PreviewAvailabilityStatus.AVAILABLE;
      })
      .catch((error) => {
        const status = error?.response?.status;
        const finalStatus = status === 404 ? PreviewAvailabilityStatus.UNAVAILABLE : PreviewAvailabilityStatus.ERROR;
        updateEntry(trackId, { status: finalStatus });
        return finalStatus;
      })
      .finally(() => {
        inflightRef.current.delete(trackId);
      });

    inflightRef.current.set(trackId, request);
    return request;
  }, [updateEntry]);

  const prefetchBatch = useCallback(
    (trackIds) => {
      (trackIds || []).forEach((trackId) => {
        if (!trackId) return;
        const status = availabilityRef.current[trackId]?.status;
        if (status === PreviewAvailabilityStatus.AVAILABLE || status === PreviewAvailabilityStatus.UNAVAILABLE) {
          return;
        }
        if (inflightRef.current.has(trackId)) {
          return;
        }
        checkAvailability(trackId);
      });
    },
    [checkAvailability],
  );

  return {
    availability,
    checkAvailability,
    prefetchBatch,
    reset,
    getStatus,
  };
};

export default usePreviewAvailability;
