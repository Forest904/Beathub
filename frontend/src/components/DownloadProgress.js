import React, { useEffect, useMemo, useRef, useState } from 'react';
import PropTypes from 'prop-types';

const INITIAL_OVERALL = {
  overall_completed: 0,
  overall_total: 0,
  overall_progress: 0,
};

const resolveStreamUrl = (baseUrl) => (baseUrl ? `${baseUrl}/api/progress/stream` : '/api/progress/stream');

const DownloadProgress = ({ visible, onClose, baseUrl, onComplete, onActiveChange }) => {
  const esRef = useRef(null);
  const completionNotified = useRef(false);
  const [overall, setOverall] = useState(INITIAL_OVERALL);
  const [songsMap, setSongsMap] = useState({}); // key -> { key, name, status, progress, lastTs }
  const [songsOrder, setSongsOrder] = useState([]); // maintain stable first-seen order

  useEffect(() => {
    if (!visible) {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      completionNotified.current = false;
      setOverall(INITIAL_OVERALL);
      setSongsMap({});
      setSongsOrder([]);
      return undefined;
    }

    const streamUrl = resolveStreamUrl(baseUrl);
    const eventSource = new EventSource(streamUrl);
    esRef.current = eventSource;

    const handleMessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (!payload) {
          return;
        }

        // Ignore job-level cancel events here; page-level polling reconciles state

        // Update overall progress snapshot
        setOverall((prev) => ({
          overall_completed: payload.overall_completed ?? prev.overall_completed ?? 0,
          overall_total: payload.overall_total ?? prev.overall_total ?? 0,
          overall_progress: payload.overall_progress ?? prev.overall_progress ?? 0,
        }));

        // Update per-song map for concurrent bars.
        // Only create bars for track-level events that include a stable id/url.
        const key = payload.song_id || payload.spotify_url;
        if (!key) {
          // Ignore album-level or non-track events (we already show an overall bar)
          return;
        }
        const name = payload.song_display_name || payload.song_name || key;
        const status = payload.status || null;
        const progress = Number(payload.progress ?? 0);
        const nowTs = Date.now();

        const normalizedProgress = Math.max(0, Math.min(100, Math.round(progress)));
        const statusLower = (status || '').toLowerCase();
        const isSongComplete = normalizedProgress >= 100 || statusLower.includes('complete') || statusLower.includes('done');

        if (isSongComplete) {
          setSongsMap((prev) => {
            if (!prev[key]) return prev;
            const next = { ...prev };
            delete next[key];
            return next;
          });
          setSongsOrder((prev) => prev.filter((k) => k !== key));
        } else {
          setSongsMap((prev) => {
            const next = { ...prev };
            next[key] = {
              key,
              name,
              status,
              progress: normalizedProgress,
              lastTs: nowTs,
            };
            return next;
          });
          setSongsOrder((prev) => (prev.includes(key) ? prev : [...prev, key]));
        }

        // Consider complete only when server reports an explicit completion status.
        // Avoid inferring completion from counts because SpotDL emits per-batch totals
        // when we chunk downloads for cooperative cancellation.
        const isComplete = (status === 'Complete');

        if (typeof onActiveChange === 'function') {
          // Active if any song is still below 100% or overall incomplete
          onActiveChange(!isComplete);
        }

        if (isComplete) {
          if (!completionNotified.current && typeof onComplete === 'function') {
            completionNotified.current = true;
            onComplete(payload);
          }
        } else {
          completionNotified.current = false;
        }
      } catch (error) {
        console.warn('Failed to parse download progress payload', error);
      }
    };

    const handleError = (error) => {
      // Let EventSource attempt auto-reconnect; do not close explicitly
      console.warn('Download progress stream error (auto-reconnecting)', error);
    };

    eventSource.addEventListener('message', handleMessage);
    eventSource.addEventListener('error', handleError);

    return () => {
      eventSource.removeEventListener('message', handleMessage);
      eventSource.removeEventListener('error', handleError);
      eventSource.close();
      if (esRef.current === eventSource) {
        esRef.current = null;
      }
    };
  }, [baseUrl, onActiveChange, onComplete, visible]);

  const overallPercentage = useMemo(() => {
    if (!overall.overall_total) return 0;
    const raw = (Number(overall.overall_completed || 0) / Number(overall.overall_total)) * 100;
    return Math.max(0, Math.min(100, Math.round(raw)));
  }, [overall.overall_completed, overall.overall_total]);

  const songList = useMemo(() => {
    // Render in stable first-seen order; completed bars are removed above
    return songsOrder.map((k) => songsMap[k]).filter(Boolean);
  }, [songsMap, songsOrder]);

  if (!visible) {
    return null;
  }

  return (
    <div className="bg-brand-50 dark:bg-gray-800 rounded-lg p-4 shadow-lg mb-6 ring-1 ring-brand-100 dark:ring-0">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-lg font-semibold">Download Progress</h3>
      </div>

      <div className="mb-3">
        <div className="text-sm text-slate-700 dark:text-gray-300">
          Overall: {overall.overall_completed} / {overall.overall_total}
        </div>
        <div className="w-full bg-brand-200 dark:bg-gray-700 rounded h-3 mt-1">
          <div className="bg-brand-600 h-3 rounded" style={{ width: `${overallPercentage}%` }} />
        </div>
      </div>

      <div className="mt-3 space-y-2">
        {songList.length === 0 ? (
          <div className="text-sm text-slate-600 dark:text-gray-400">Waiting for songs…</div>
        ) : (
          songList.map((s) => (
            <div key={s.key} className="w-full">
              <div className="flex items-center justify-between">
                <div className="text-sm text-slate-700 dark:text-gray-300 truncate pr-2">{s.name || 'Unknown'}</div>
                <div className="text-xs text-slate-500 dark:text-gray-400 whitespace-nowrap">{s.progress || 0}%</div>
              </div>
              <div className="w-full bg-brand-200 dark:bg-gray-700 rounded h-2 mt-1">
                <div className="bg-brandSuccess-500 h-2 rounded" style={{ width: `${Number(s.progress || 0)}%` }} />
              </div>
              {s.status && (
                <div className="text-xs text-slate-500 dark:text-gray-400 mt-1">{s.status}</div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

DownloadProgress.propTypes = {
  visible: PropTypes.bool,
  onClose: PropTypes.func.isRequired,
  baseUrl: PropTypes.string,
  onComplete: PropTypes.func,
  onActiveChange: PropTypes.func,
};

DownloadProgress.defaultProps = {
  visible: false,
  baseUrl: undefined,
  onComplete: undefined,
  onActiveChange: undefined,
};

export default DownloadProgress;
