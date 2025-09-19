import React, { useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';

const INITIAL_STATE = {
  status: 'Idle',
  progress: 0,
  message: null,
  phase: null,
  trackIndex: null,
  trackTotal: null,
  elapsedSec: null,
};

const phaseLabel = (phase) => {
  if (!phase) {
    return 'Working';
  }

  switch (phase) {
    case 'preparing':
      return 'Preparing';
    case 'converting':
      return 'Converting';
    case 'staging':
      return 'Staging';
    case 'burning':
      return 'Burning';
    case 'completed':
      return 'Completed';
    default:
      return phase;
  }
};

const BurnProgress = ({ visible, baseUrl, sessionId, onClose }) => {
  const esRef = useRef(null);
  const [state, setState] = useState(INITIAL_STATE);

  useEffect(() => {
    if (!visible) {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      setState(INITIAL_STATE);
      return undefined;
    }

    const streamUrl = baseUrl ? `${baseUrl}/api/progress/stream` : '/api/progress/stream';
    const source = new EventSource(streamUrl);
    esRef.current = source;

    const handleMessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (!payload || !payload.event) {
          return;
        }

        if (sessionId && payload.session_id && payload.session_id !== sessionId) {
          return;
        }

        if (payload.event === 'cd_burn_progress') {
          setState({
            status: payload.status || 'Burning',
            progress: payload.progress || 0,
            message: payload.message || null,
            phase: payload.phase || null,
            trackIndex: payload.track_index || null,
            trackTotal: payload.track_total || null,
            elapsedSec: payload.elapsed_sec || null,
          });
        }

        if (payload.event === 'cd_burn_complete') {
          setState({
            status: 'Completed',
            progress: 100,
            message: payload.message || 'Completed',
            phase: 'completed',
            trackIndex: null,
            trackTotal: null,
            elapsedSec: null,
          });
          // Auto-hide after a short delay for a subtle finish
          setTimeout(() => {
            if (typeof onClose === 'function') {
              onClose();
            }
          }, 1500);
        }
      } catch (error) {
        console.warn('Failed to parse burn progress event', error);
      }
    };

    const handleError = (error) => {
      console.warn('Burn progress stream error', error);
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
    };

    source.addEventListener('message', handleMessage);
    source.addEventListener('error', handleError);

    return () => {
      source.removeEventListener('message', handleMessage);
      source.removeEventListener('error', handleError);
      source.close();
      if (esRef.current === source) {
        esRef.current = null;
      }
    };
  }, [baseUrl, sessionId, visible]);

  if (!visible) {
    return null;
  }

  return (
    <div className="bg-brand-50 dark:bg-gray-800 rounded-lg p-4 shadow-lg mb-6 ring-1 ring-brand-100 dark:ring-0">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-lg font-semibold">Burn Progress</h3>
        <button type="button" onClick={onClose} className="text-sm text-slate-600 hover:text-slate-900 dark:text-gray-300 dark:hover:text-white">
          Hide
        </button>
      </div>
      <div className="text-sm text-slate-700 dark:text-gray-300 mb-1">{state.message || state.status}</div>
      <div className="text-xs text-slate-600 dark:text-gray-400 mb-2">
        Phase: {phaseLabel(state.phase)}
        {state.trackIndex && state.trackTotal ? ` - Track ${state.trackIndex}/${state.trackTotal}` : ''}
        {typeof state.elapsedSec === 'number' ? ` - ${state.elapsedSec}s` : ''}
      </div>
      <div className="w-full bg-brand-200 dark:bg-gray-700 rounded h-3 mt-1">
        <div className="bg-brand-600 h-3 rounded" style={{ width: `${state.progress || 0}%` }} />
      </div>
    </div>
  );
};

BurnProgress.propTypes = {
  visible: PropTypes.bool,
  baseUrl: PropTypes.string,
  sessionId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  onClose: PropTypes.func.isRequired,
};

BurnProgress.defaultProps = {
  visible: false,
  baseUrl: undefined,
  sessionId: undefined,
};

export default BurnProgress;
