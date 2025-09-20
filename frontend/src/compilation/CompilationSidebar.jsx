import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useCompilation } from './CompilationContext.jsx';
import { formatDuration } from '../utils/helpers';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const SidebarContent = () => {
  const navigate = useNavigate();
  const { compilationMode, setCompilationMode, name, rename, items, totalMs, clear, remove, reorder, capacityMinutes, altCapacityMinutes, coverDataUrl, setCoverDataUrl, clearCover } = useCompilation();
  const [submitting, setSubmitting] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [nameError, setNameError] = useState(false);
  const fileInputRef = useRef(null);
  const nameInputRef = useRef(null);
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
          <h2 className="text-xl font-semibold">
            <span className="inline-block rounded-md bg-brand-600 px-2 py-1 text-white dark:bg-brandDark-600">Make you own compilation</span>
          </h2>
          <button
            type="button"
            onClick={() => setCompilationMode(false)}
            className="inline-flex items-center justify-center rounded-md border border-slate-300 p-2 text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            title="Hide sidebar"
            aria-label="Hide sidebar"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
              <path fillRule="evenodd" d="M15.53 4.47a.75.75 0 010 1.06L9.06 12l6.47 6.47a.75.75 0 11-1.06 1.06l-7-7a.75.75 0 010-1.06l7-7a.75.75 0 011.06 0z" clipRule="evenodd" />
            </svg>
          </button>
        </div>

        {/* Content area:info + list (list scrolls) */}
        <div className="flex-1 min-h-0 flex flex-col overflow-hidden pr-1">
          {/* Row: cover + name */}
          <div className="mb-3 flex items-center gap-3">
            <div
              className="relative w-16 aspect-square rounded-md border border-slate-300 bg-slate-100 dark:border-slate-700 dark:bg-slate-800 overflow-hidden cursor-pointer"
              onClick={() => fileInputRef.current && fileInputRef.current.click()}
              onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
              onDrop={(e) => {
                e.preventDefault();
                e.stopPropagation();
                const file = e.dataTransfer.files && e.dataTransfer.files[0];
                if (!file) return;
                const maxBytes = 5 * 1024 * 1024;
                if (!file.type.startsWith('image/')) { alert('Please drop an image file.'); return; }
                if (file.size > maxBytes) { alert('Image too large. Max 5 MB.'); return; }
                const reader = new FileReader();
                reader.onload = () => setCoverDataUrl(String(reader.result || ''));
                reader.readAsDataURL(file);
              }}
              role="button"
              tabIndex={0}
            >
              {coverDataUrl ? (
                <img src={coverDataUrl} alt="Compilation cover" className="absolute inset-0 h-full w-full object-cover" />
              ) : (
                <div className="absolute inset-0 flex items-center justify-center text-[10px] text-slate-500 dark:text-slate-300">Cover</div>
              )}
              {coverDataUrl && (
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); clearCover(); }}
                  className="absolute -right-2 -top-2 rounded-full bg-slate-100 p-1 text-slate-600 shadow hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                  title="Remove cover"
                  aria-label="Remove cover"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-3 w-3"><path fillRule="evenodd" d="M5.47 5.47a.75.75 0 011.06 0L12 10.94l5.47-5.47a.75.75 0 111.06 1.06L13.06 12l5.47 5.47a.75.75 0 11-1.06 1.06L12 13.06l-5.47 5.47a.75.75 0 11-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 010-1.06z" clipRule="evenodd" /></svg>
                </button>
              )}
              <input
                type="file"
                ref={fileInputRef}
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files && e.target.files[0];
                  if (!file) return;
                  const maxBytes = 5 * 1024 * 1024;
                  if (!file.type.startsWith('image/')) { alert('Please select an image file.'); return; }
                  if (file.size > maxBytes) { alert('Image too large. Max 5 MB.'); return; }
                  const reader = new FileReader();
                  reader.onload = () => setCoverDataUrl(String(reader.result || ''));
                  reader.readAsDataURL(file);
                }}
              />
            </div>
            <div className="flex-1">
              <label htmlFor="compilation-name" className="mb-1 block text-sm text-slate-700 dark:text-slate-300">Name</label>
              <input
                ref={nameInputRef}
                id="compilation-name"
                type="text"
                value={name}
                onChange={(e) => { const v = e.target.value; rename(v); if ((v || '').trim()) setNameError(false); }}
                aria-invalid={nameError ? 'true' : 'false'}
                placeholder="My Compilation"
                className={`w-full rounded-md bg-white px-2 py-1.5 text-sm text-slate-900 outline-none focus:ring-2 dark:bg-slate-800 dark:text-slate-100 ${nameError ? 'border border-brandError-600 focus:ring-brandError-500 dark:border-brandError-700' : 'border border-slate-300 focus:ring-brand-500 dark:border-slate-700'}`}
              />
            </div>
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

        <div className="mb-3"></div>

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
        <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={() => {
              // eslint-disable-next-line no-alert
              const ok = window.confirm('Clear all tracks from the compilation?');
              if (ok) clear();
            }}
            className="inline-flex items-center justify-center rounded-md border border-slate-300 bg-white p-2 text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            title="Clear all"
            aria-label="Clear all"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
              <path d="M9 3.75A2.25 2.25 0 0 1 11.25 1.5h1.5A2.25 2.25 0 0 1 15 3.75V4.5h3.75a.75.75 0 0 1 0 1.5H5.25a.75.75 0 0 1 0-1.5H9V3.75z" />
              <path fillRule="evenodd" d="M5.78 7.5h12.44l-.8 12.04A2.25 2.25 0 0 1 15.18 21.75H8.82a2.25 2.25 0 0 1-2.24-2.21L5.78 7.5zm4.22 3.75a.75.75 0 0 0-1.5 0v6a.75.75 0 0 0 1.5 0v-6zm4.5 0a.75.75 0 0 0-1.5 0v6a.75.75 0 0 0 1.5 0v-6z" clipRule="evenodd" />
            </svg>
          </button>
          <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={items.length === 0 || !name || !name.trim()}
            onClick={() => {
              if (!name || !name.trim()) {
                setNameError(true);
                try { nameInputRef.current && nameInputRef.current.focus(); } catch (e) {}
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
