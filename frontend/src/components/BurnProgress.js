// frontend/src/components/BurnProgress.js
import React, { useEffect, useRef, useState } from 'react';

export default function BurnProgress({ visible, baseUrl, sessionId, onClose }) {
  const esRef = useRef(null);
  const [state, setState] = useState({
    status: 'Idle',
    progress: 0,
    message: null,
    phase: null,
    trackIndex: null,
    trackTotal: null,
    elapsedSec: null,
  });

  useEffect(() => {
    if (!visible) {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      return;
    }

    const url = baseUrl ? `${baseUrl}/api/progress/stream` : '/api/progress/stream';
    const es = new EventSource(url);
    esRef.current = es;
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        // Expect cd_burn_progress / cd_burn_complete events; optionally filter by session_id when present
        if (!data || !data.event) return;
        if (sessionId && data.session_id && data.session_id !== sessionId) return;
        if (data.event === 'cd_burn_progress') {
          setState({
            status: data.status || 'burning',
            progress: data.progress || 0,
            message: data.message || null,
            phase: data.phase || null,
            trackIndex: data.track_index || null,
            trackTotal: data.track_total || null,
            elapsedSec: data.elapsed_sec || null,
          });
        } else if (data.event === 'cd_burn_complete') {
          setState({ status: 'completed', progress: 100, message: 'Completed', phase: 'completed', trackIndex: null, trackTotal: null, elapsedSec: null });
        }
      } catch (_) {}
    };
    es.onerror = () => {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
    };
    return () => {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
    };
  }, [visible, baseUrl, sessionId]);

  if (!visible) return null;
  const prettyPhase = (p) => {
    if (!p) return 'working';
    switch (p) {
      case 'preparing': return 'Preparing';
      case 'converting': return 'Converting';
      case 'staging': return 'Staging';
      case 'burning': return 'Burning';
      case 'completed': return 'Completed';
      default: return String(p);
    }
  };
  return (
    <div className="bg-gray-800 rounded-lg p-4 shadow-lg mb-6">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-lg font-semibold">Burn Progress</h3>
        <button onClick={onClose} className="text-sm text-gray-300 hover:text-white">Hide</button>
      </div>
      <div className="text-sm text-gray-300 mb-1">{state.message || state.status}</div>
      <div className="text-xs text-gray-400 mb-2">
        Phase: {prettyPhase(state.phase)}
        {state.trackIndex && state.trackTotal ? (
          <> • Track {state.trackIndex}/{state.trackTotal}</>
        ) : null}
        {typeof state.elapsedSec === 'number' ? (
          <> • {state.elapsedSec}s</>
        ) : null}
      </div>
      <div className="w-full bg-gray-700 rounded h-3 mt-1">
        <div className="bg-red-500 h-3 rounded" style={{ width: `${state.progress || 0}%` }}></div>
      </div>
    </div>
  );
}
