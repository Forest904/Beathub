import React, { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { useCompilation } from './CompilationContext.jsx';
import { formatDuration } from '../utils/helpers';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const SidebarContent = () => {
  const navigate = useNavigate();
  const { compilationMode, setCompilationMode, name, rename, items, totalMs, clear, remove, reorder, capacityMinutes, altCapacityMinutes } = useCompilation();
  const [submitting, setSubmitting] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const capacityMs = Math.max(0, Number(capacityMinutes || 0)) * 60000;
  const overBudget = Number(totalMs || 0) > capacityMs;
  const overByMs = Math.max(0, Number(totalMs || 0) - capacityMs);

  const formattedBudget = useMemo(() => {
    const mins = Math.max(0, Math.floor((capacityMs) / 60000));
    const sec = Math.max(0, Math.round(((capacityMs) % 60000) / 1000));
    return `${mins}:${sec < 10 ? '0' : ''}${sec}`;
  }, [capacityMs]);

  // Close on Escape
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') setCompilationMode(false);
    };
    if (compilationMode) {
      document.addEventListener('keydown', handler);
      return () => document.removeEventListener('keydown', handler);
    }
    return undefined;
  }, [compilationMode, setCompilationMode]);

  // Reset confirmation if name/items change
  useEffect(() => {
    setConfirmed(false);
  }, [name, items]);

  if (!compilationMode) return null;

  return (
    <div className="fixed inset-0 z-40">
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/40" onClick={() => setCompilationMode(false)} />

      {/* Drawer */}
      <aside className="absolute inset-y-0 left-0 w-[22rem] max-w-[90vw] bg-white p-4 shadow-xl dark:bg-slate-900 flex flex-col">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold">Compilation</h2>
          <button
            type="button"
            onClick={() => setCompilationMode(false)}
            className="rounded-md border border-slate-300 px-2 py-1 text-sm hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            Close
          </button>
        </div>

        {/* Scrollable content start */}
        <div className="flex-1 min-h-0 overflow-y-auto pr-1">
        {/* Cover placeholder */}
        <div className="mb-3">
          <div className="w-32 aspect-square rounded-md bg-slate-200 dark:bg-slate-700 flex items-center justify-center text-[11px] text-slate-600 dark:text-slate-300">
            Cover Placeholder
          </div>
        </div>

        <div className="mb-3">
          <label htmlFor="compilation-name" className="mb-1 block text-sm text-slate-600 dark:text-slate-300">Name</label>
          <input
            id="compilation-name"
            type="text"
            value={name}
            onChange={(e) => rename(e.target.value)}
            placeholder="My Compilation"
            className="w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-brand-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          />
        </div>

        <div className="mb-2 text-sm">
          <div className="text-slate-600 dark:text-slate-300">
            Total: <span className={`font-medium ${overBudget ? 'text-brandWarning-600 dark:text-brandWarning-500' : 'text-slate-900 dark:text-white'}`}>{formatDuration(totalMs)}</span>
          </div>
          <div className="mt-1 text-xs text-slate-600 dark:text-slate-300">
            CD Budget: <span className="font-medium">{formattedBudget}</span>
            {altCapacityMinutes > 0 && <span className="ml-2">(Alt: {altCapacityMinutes}m)</span>}
            {overBudget && (
              <span className="ml-2 text-brandWarning-600 dark:text-brandWarning-500 font-semibold">Over by {formatDuration(overByMs)}</span>
            )}
          </div>
        </div>

        <div className="mb-3 flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              // eslint-disable-next-line no-alert
              const ok = window.confirm('Clear all tracks from the compilation?');
              if (ok) clear();
            }}
            className="rounded-md border border-brand-300 bg-white px-2 py-1.5 text-sm text-brand-700 hover:bg-brand-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            Clear
          </button>
          <button
            type="button"
            disabled={items.length === 0}
            onClick={() => {
              if (items.length === 0) return;
              const sanitize = (s) => (s || '').replace(/[\\/:*?"<>|]/g, '_').replace(/_{2,}/g, '_').trim();
              const safeName = sanitize(name || 'My Compilation');
              const lines = ['#EXTM3U'];
              items.forEach((t) => {
                const secs = Math.round(((t?.duration_ms) || 0) / 1000);
                const artist = Array.isArray(t?.artists) ? t.artists.join(', ') : '';
                const title = t?.title || 'Unknown';
                lines.push(`#EXTINF:${Number.isFinite(secs) ? secs : 0},${artist ? `${artist} - ` : ''}${title}`);
                const url = t?.spotify_url || t?.url || (t?.spotify_id ? `https://open.spotify.com/track/${t.spotify_id}` : title);
                lines.push(String(url));
              });
              const blob = new Blob([lines.join('\n') + '\n'], { type: 'audio/x-mpegurl' });
              const a = document.createElement('a');
              a.href = URL.createObjectURL(blob);
              a.download = `${safeName}.m3u`;
              document.body.appendChild(a);
              a.click();
              setTimeout(() => {
                URL.revokeObjectURL(a.href);
                a.remove();
              }, 0);
            }}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${items.length === 0 ? 'bg-slate-200 text-slate-400 cursor-not-allowed dark:bg-slate-800 dark:text-slate-600' : 'bg-slate-200 hover:bg-slate-300 text-slate-700 dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-slate-200'}`}
          >
            Save .m3u
          </button>
        </div>

        <div className="mt-4 rounded-md border border-slate-200 p-2 dark:border-slate-700">
          {items.length === 0 ? (
            <p className="px-1 py-2 text-sm text-slate-500 dark:text-slate-400">No tracks yet. Add from albums or artists.</p>
          ) : (
            <ul className="space-y-1">
              {items.map((t, idx) => {
                const id = (t.spotify_id || t.id || t.url || t.uri) ?? String(idx);
                const canUp = idx > 0;
                const canDown = idx < items.length - 1;
                return (
                  <li key={id} className="rounded-md border border-slate-200 p-2 dark:border-slate-700">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium text-slate-900 dark:text-white" title={t.title}>{t.title || 'Untitled track'}</div>
                        <div className="truncate text-xs text-slate-600 dark:text-slate-300" title={(t.artists || []).join(', ')}>
                          {(t.artists || []).join(', ')}
                        </div>
                      </div>
                      <div className="flex shrink-0 items-center gap-1">
                        <button
                          type="button"
                          onClick={() => remove(id)}
                          className="rounded border border-brandError-600 px-2 py-1 text-xs text-brandError-700 hover:bg-brandError-50 dark:border-brandError-700 dark:text-brandError-400 dark:hover:bg-brandError-900/30"
                          title="Remove from compilation"
                        >
                          Remove
                        </button>
                        <button
                          type="button"
                          onClick={() => canUp && reorder(idx, idx - 1)}
                          disabled={!canUp}
                          className={`rounded border px-2 py-1 text-xs ${canUp ? 'border-slate-300 hover:bg-slate-50 dark:border-slate-600 dark:hover:bg-slate-800' : 'border-slate-200 text-slate-300 dark:border-slate-700 dark:text-slate-600 cursor-not-allowed'}`}
                          title="Move up"
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          onClick={() => canDown && reorder(idx, idx + 1)}
                          disabled={!canDown}
                          className={`rounded border px-2 py-1 text-xs ${canDown ? 'border-slate-300 hover:bg-slate-50 dark:border-slate-600 dark:hover:bg-slate-800' : 'border-slate-200 text-slate-300 dark:border-slate-700 dark:text-slate-600 cursor-not-allowed'}`}
                          title="Move down"
                        >
                          ↓
                        </button>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
        
        </div>

        {/* Footer actions: confirm then download */}
        <div className="mt-3 flex items-center justify-end gap-2">
          <button
            type="button"
            disabled={items.length === 0 || !name || !name.trim()}
            onClick={() => {
              if (!name || !name.trim()) {
                // eslint-disable-next-line no-alert
                alert('Please enter a compilation name first.');
                return;
              }
              setConfirmed(true);
            }}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${items.length === 0 || !name || !name.trim() ? 'bg-slate-200 text-slate-400 cursor-not-allowed dark:bg-slate-800 dark:text-slate-600' : 'bg-slate-200 hover:bg-slate-300 text-slate-700 dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-slate-200'}`}
          >
            Confirm Compilation
          </button>
          <button
            type="button"
            disabled={submitting || !confirmed || items.length === 0 || !name || !name.trim()}
            onClick={async () => {
              if (!confirmed || items.length === 0) return;
              setSubmitting(true);
              try {
                const payload = { name, tracks: items, async: true };
                const res = await axios.post('/api/compilations/download', payload);
                const compId = res.data?.compilation_spotify_id;
                clear();
                setCompilationMode(false);
                setConfirmed(false);
                navigate('/download', { state: { showProgressPanel: true, selectSpotifyId: compId } });
              } catch (e) {
                // eslint-disable-next-line no-alert
                alert('Failed to start compilation download.');
              } finally {
                setSubmitting(false);
              }
            }}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${submitting || !confirmed || items.length === 0 || !name || !name.trim() ? 'bg-slate-200 text-slate-400 cursor-not-allowed dark:bg-slate-800 dark:text-slate-600' : 'bg-brand-600 text-white hover:bg-brand-700 dark:bg-brandDark-600 dark:hover:bg-brandDark-500'}`}
          >
            {submitting ? 'Starting…' : 'Direct Download'}
          </button>
        </div>
      </aside>
    </div>
  );
};

const CompilationSidebar = () => {
  if (typeof document === 'undefined') return null;
  return createPortal(<SidebarContent />, document.body);
};

export default CompilationSidebar;


