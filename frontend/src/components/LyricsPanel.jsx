import React, { useEffect, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import axios from 'axios';

const Backdrop = ({ visible, onClick }) => (
  <div
    className={`${visible ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'} fixed inset-0 bg-black/30 transition-opacity duration-200`}
    onClick={(e) => { e.stopPropagation(); if (onClick) onClick(e); }}
    aria-hidden="true"
  />
);

Backdrop.propTypes = {
  visible: PropTypes.bool.isRequired,
  onClick: PropTypes.func,
};

const LyricsPanel = ({ visible, onClose, baseUrl, albumId, track }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lyrics, setLyrics] = useState(null);
  const [copied, setCopied] = useState(false);

  const title = track?.title || track?.name || '';
  const artist = useMemo(() => {
    const arr = track?.artists || [];
    if (Array.isArray(arr) && arr.length > 0) return arr[0];
    if (typeof track?.artist === 'string') return track.artist;
    return '';
  }, [track]);

  useEffect(() => {
    if (!visible || !albumId || !title) {
      return;
    }
    let cancelled = false;
    async function fetchLyrics() {
      setLoading(true);
      setError(null);
      setLyrics(null);
      try {
        const response = await axios.get(`${baseUrl || ''}/api/items/${albumId}/lyrics`, {
          params: { title, artist },
        });
        if (!cancelled) {
          setLyrics(response.data?.lyrics || null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            (err?.response?.data?.message || err?.message || 'Lyrics not found for this track.'),
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchLyrics();
    return () => {
      cancelled = true;
    };
  }, [visible, albumId, title, artist, baseUrl]);

  useEffect(() => {
    if (!visible) {
      setCopied(false);
    }
  }, [visible]);

  const handleCopy = async () => {
    if (!lyrics) return;
    try {
      await navigator.clipboard.writeText(lyrics);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (e) {
      // Fallback
      try {
        const area = document.createElement('textarea');
        area.value = lyrics;
        area.style.position = 'fixed';
        area.style.top = '-1000px';
        document.body.appendChild(area);
        area.focus();
        area.select();
        document.execCommand('copy');
        document.body.removeChild(area);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      } catch (_) {
        // ignore
      }
    }
  };

  const headerTitle = useMemo(() => {
    const a = artist || 'Unknown Artist';
    const t = title || 'Unknown Title';
    return `${t} — ${a}'s lyrics`;
  }, [artist, title]);

  return (
    <>
      <Backdrop visible={visible} onClick={onClose} />
      <aside
        className={`fixed top-0 right-0 h-full w-full max-w-lg bg-white dark:bg-gray-900 shadow-xl border-l border-gray-200 dark:border-gray-700 z-50 transform transition-transform duration-200 ${visible ? 'translate-x-0' : 'translate-x-full'}`}
        onClick={(e) => e.stopPropagation()}
        aria-hidden={!visible}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white truncate mr-3" title={headerTitle}>{headerTitle}</h3>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleCopy}
              disabled={!lyrics}
              className={`px-2 py-1 rounded text-sm border transition-colors ${lyrics ? 'border-slate-300 text-slate-700 hover:bg-slate-100 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800' : 'border-slate-200 text-slate-400 dark:border-gray-800 dark:text-gray-600 cursor-not-allowed'}`}
              title={lyrics ? (copied ? 'Copied!' : 'Copy lyrics') : 'No lyrics to copy'}
            >
              {copied ? 'Copied' : 'Copy'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-2 py-1 rounded text-slate-600 hover:text-slate-900 dark:text-gray-300 dark:hover:text-white"
              aria-label="Close lyrics panel"
            >
              ✕
            </button>
          </div>
        </div>
        <div className="p-4 h-[calc(100%-3.25rem)] overflow-y-auto">
          {loading && (
            <div className="text-center mt-4">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-brand-600 dark:border-brandDark-500 mx-auto" />
              <p className="text-slate-600 dark:text-gray-300 mt-2">Loading lyrics...</p>
            </div>
          )}
          {!loading && error && (
            <div className="bg-brand-50 dark:bg-gray-800 border border-brand-200 dark:border-gray-700 rounded p-3 text-slate-700 dark:text-gray-300">
              {error}
            </div>
          )}
          {!loading && !error && lyrics && (
            <div className="whitespace-pre-wrap text-slate-900 dark:text-gray-100 leading-relaxed text-sm">
              {lyrics}
            </div>
          )}
          {!loading && !error && !lyrics && (
            <div className="text-slate-600 dark:text-gray-300">No lyrics to display.</div>
          )}
        </div>
      </aside>
    </>
  );
};

LyricsPanel.propTypes = {
  visible: PropTypes.bool,
  onClose: PropTypes.func,
  baseUrl: PropTypes.string,
  albumId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  track: PropTypes.shape({
    title: PropTypes.string,
    name: PropTypes.string,
    artists: PropTypes.arrayOf(PropTypes.string),
    artist: PropTypes.string,
  }),
};

LyricsPanel.defaultProps = {
  visible: false,
  onClose: undefined,
  baseUrl: '',
  albumId: null,
  track: null,
};

export default LyricsPanel;
