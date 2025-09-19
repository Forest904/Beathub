import React, { useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';

const INITIAL_STATE = {
  song_display_name: null,
  status: null,
  progress: 0,
  overall_completed: 0,
  overall_total: 0,
};

const resolveStreamUrl = (baseUrl) => (baseUrl ? `${baseUrl}/api/progress/stream` : '/api/progress/stream');

const ProgressPanel = ({ visible, onClose, baseUrl, onComplete, onActiveChange }) => {
  const esRef = useRef(null);
  const completionNotified = useRef(false);
  const [state, setState] = useState(INITIAL_STATE);

  useEffect(() => {
    if (!visible) {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      completionNotified.current = false;
      setState(INITIAL_STATE);
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

        const next = {
          song_display_name: payload.song_display_name ?? payload.song_name ?? null,
          status: payload.status ?? null,
          progress: payload.progress ?? 0,
          overall_completed: payload.overall_completed ?? 0,
          overall_total: payload.overall_total ?? 0,
        };

        setState(next);

        const total = Number(next.overall_total || 0);
        const done = Number(next.overall_completed || 0);
        const isComplete = next.status === 'Complete' || (total > 0 && done >= total);

        if (typeof onActiveChange === 'function') {
          onActiveChange(!isComplete);
        }

        if (isComplete) {
          if (!completionNotified.current && typeof onComplete === 'function') {
            completionNotified.current = true;
            onComplete(next);
          }
        } else {
          completionNotified.current = false;
        }
      } catch (error) {
        console.warn('Failed to parse download progress payload', error);
      }
    };

    const handleError = (error) => {
      console.warn('Download progress stream error', error);
      eventSource.close();
      if (esRef.current === eventSource) {
        esRef.current = null;
      }
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

  if (!visible) {
    return null;
  }

  const overallPercentage = (() => {
    if (!state.overall_total) {
      return 0;
    }
    const raw = (Number(state.overall_completed || 0) / Number(state.overall_total)) * 100;
    return Math.max(0, Math.min(100, Math.round(raw)));
  })();

  return (
    <div className="bg-brand-50 dark:bg-gray-800 rounded-lg p-4 shadow-lg mb-6 ring-1 ring-brand-100 dark:ring-0">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-lg font-semibold">Download Progress</h3>
        <button type="button" onClick={onClose} className="text-sm text-slate-600 hover:text-slate-900 dark:text-gray-300 dark:hover:text-white">
          Hide
        </button>
      </div>

      <div className="mb-3">
        <div className="text-sm text-slate-700 dark:text-gray-300">
          Overall: {state.overall_completed} / {state.overall_total}
        </div>
        <div className="w-full bg-brand-200 dark:bg-gray-700 rounded h-3 mt-1">
          <div className="bg-brand-600 h-3 rounded" style={{ width: `${overallPercentage}%` }} />
        </div>
      </div>

      <div className="mt-3">
        <div className="text-sm text-slate-700 dark:text-gray-300">{state.status || 'Waiting...'}</div>
        <div className="text-sm text-slate-600 dark:text-gray-400 truncate">{state.song_display_name || 'Unknown'}</div>
        <div className="w-full bg-brand-200 dark:bg-gray-700 rounded h-2 mt-1">
          <div className="bg-brandSuccess-500 h-2 rounded" style={{ width: `${state.progress || 0}%` }} />
        </div>
      </div>
    </div>
  );
};

ProgressPanel.propTypes = {
  visible: PropTypes.bool,
  onClose: PropTypes.func.isRequired,
  baseUrl: PropTypes.string,
  onComplete: PropTypes.func,
  onActiveChange: PropTypes.func,
};

ProgressPanel.defaultProps = {
  visible: false,
  baseUrl: undefined,
  onComplete: undefined,
  onActiveChange: undefined,
};

export default ProgressPanel;
