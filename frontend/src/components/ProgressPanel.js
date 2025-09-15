// frontend/src/components/ProgressPanel.js
import React, { useEffect, useRef, useState } from 'react';

function ProgressPanel({ visible, onClose, baseUrl, onComplete, onActiveChange }) {
  const esRef = useRef(null);
  const [state, setState] = useState({
    song_display_name: null,
    status: null,
    progress: 0,
    overall_completed: 0,
    overall_total: 0,
    overall_progress: 0,
  });

  useEffect(() => {
    if (!visible) {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      return;
    }

    try {
      const url = baseUrl ? `${baseUrl}/api/progress/stream` : '/api/progress/stream';
      const es = new EventSource(url);
      esRef.current = es;
      es.onopen = () => {
        if (process.env.NODE_ENV !== 'production') {
          // eslint-disable-next-line no-console
          console.log('[SSE] connected to', url);
        }
      };
      es.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          setState((prev) => {
            const next = { ...prev, ...data };
            // Determine active/completed state from incoming payload
            const total = Number(next.overall_total || 0);
            const done = Number(next.overall_completed || 0);
            const isComplete = (next.status === 'Complete') || (total > 0 && done >= total);
            if (typeof onActiveChange === 'function') {
              try {
                onActiveChange(!isComplete);
              } catch (_) {}
            }
            if (isComplete && typeof onComplete === 'function') {
              try {
                onComplete(next);
              } catch (_) {}
            }
            return next;
          });
        } catch (_) {
          // ignore
        }
      };
      es.onerror = (e) => {
        if (process.env.NODE_ENV !== 'production') {
          // eslint-disable-next-line no-console
          console.warn('[SSE] error on', url, e);
        }
        // auto-close on error to avoid leaking connections
        if (esRef.current) {
          esRef.current.close();
          esRef.current = null;
        }
      };
    } catch (_) {
      // ignore
    }

    return () => {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
    };
  }, [visible, baseUrl, onComplete, onActiveChange]);

  if (!visible) return null;

  const {
    song_display_name,
    status,
    progress,
    overall_completed,
    overall_total,
  } = state;

  const overallPct = (() => {
    if (!overall_total) return 0;
    const per = Math.min(100, Math.max(0, Math.round((overall_completed / overall_total) * 100)));
    return per;
  })();

  return (
    <div className="bg-gray-800 rounded-lg p-4 shadow-lg mb-6">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-lg font-semibold">Download Progress</h3>
        <button onClick={onClose} className="text-sm text-gray-300 hover:text-white">Hide</button>
      </div>

      <div className="mb-3">
        <div className="text-sm text-gray-300">Overall: {overall_completed} / {overall_total}</div>
        <div className="w-full bg-gray-700 rounded h-3 mt-1">
          <div className="bg-blue-500 h-3 rounded" style={{ width: `${overallPct}%` }}></div>
        </div>
      </div>

      <div className="mt-3">
        <div className="text-sm text-gray-300">{status || 'Waiting...'}</div>
        <div className="text-sm text-gray-400 truncate">{song_display_name || 'Unknown'}</div>
        <div className="w-full bg-gray-700 rounded h-2 mt-1">
          <div className="bg-green-500 h-2 rounded" style={{ width: `${progress || 0}%` }}></div>
        </div>
      </div>
    </div>
  );
}

export default ProgressPanel;

