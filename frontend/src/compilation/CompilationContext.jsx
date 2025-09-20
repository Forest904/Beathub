import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';

// Local storage key and versioning
const STORAGE_KEY = 'compilation:v1';

const defaultState = {
  name: 'My Compilation',
  items: [],
  totalMs: 0,
  coverDataUrl: null,
};

const CompilationContext = createContext(null);

export const CompilationProvider = ({ children }) => {
  const didHydrate = useRef(false);

  // Cart state
  const [name, setName] = useState(defaultState.name);
  const [items, setItems] = useState(defaultState.items);
  const [coverDataUrl, setCoverDataUrl] = useState(defaultState.coverDataUrl);
  const [capacityMinutes, setCapacityMinutes] = useState(80);
  const [altCapacityMinutes, setAltCapacityMinutes] = useState(0);

  // UI state (not persisted): whether user is in Compilation Mode
  const [compilationMode, setCompilationMode] = useState(false);

  // Derived total duration
  const totalMs = useMemo(() => items.reduce((sum, t) => sum + (Number(t?.duration_ms) || 0), 0), [items]);

  // Hydrate from localStorage once on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === 'object') {
          if (typeof parsed.name === 'string') setName(parsed.name);
          if (Array.isArray(parsed.items)) setItems(parsed.items);
          if (typeof parsed.coverDataUrl === 'string' || parsed.coverDataUrl === null) setCoverDataUrl(parsed.coverDataUrl || null);
        }
      }
    } catch (e) {
      // ignore malformed storage
      // eslint-disable-next-line no-console
      console.warn('Failed to load compilation from storage', e);
    } finally {
      didHydrate.current = true;
    }
  }, []);

  // Persist when name/items change (after initial hydration)
  useEffect(() => {
    if (!didHydrate.current) return;
    try {
      const toSave = { name, items, coverDataUrl };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn('Failed to persist compilation to storage', e);
    }
  }, [name, items, coverDataUrl]);

  // Fetch frontend config (capacity minutes)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await axios.get('/api/config/frontend');
        const data = res.data || {};
        if (!cancelled) {
          if (typeof data.cd_capacity_minutes === 'number') setCapacityMinutes(data.cd_capacity_minutes);
          if (typeof data.cd_alt_capacity_minutes === 'number') setAltCapacityMinutes(data.cd_alt_capacity_minutes);
        }
      } catch (e) {
        // ignore; defaults will be used
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // API methods
  const add = (track) => {
    if (!track) return;
    const id = track.spotify_id || track.id || track.url || track.uri;
    if (!id) return;
    setItems((prev) => {
      if (prev.some((t) => (t.spotify_id || t.id || t.url || t.uri) === id)) return prev; // no duplicates
      return [...prev, track];
    });
  };

  const remove = (spotifyId) => {
    if (!spotifyId) return;
    setItems((prev) => prev.filter((t) => (t.spotify_id || t.id || t.url || t.uri) !== spotifyId));
  };

  const clear = () => {
    setItems([]);
  };

  const rename = (newName) => {
    setName((newName || '').slice(0, 200));
  };

  const clearCover = () => setCoverDataUrl(null);

  const reorder = (from, to) => {
    setItems((prev) => {
      const next = prev.slice();
      if (from < 0 || from >= next.length || to < 0 || to >= next.length) return prev;
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      return next;
    });
  };

  const isInCompilation = (id) => {
    if (!id) return false;
    return items.some((t) => (t.spotify_id || t.id || t.url || t.uri) === id);
  };

  const value = useMemo(() => ({
    // data
    name,
    items,
    totalMs,
    itemCount: items.length,
    coverDataUrl,
    capacityMinutes,
    altCapacityMinutes,
    // ui
    compilationMode,
    setCompilationMode,
    toggleCompilationMode: () => setCompilationMode((v) => !v),
    // actions
    add,
    remove,
    clear,
    rename,
    setCoverDataUrl,
    clearCover,
    reorder,
    isInCompilation,
  }), [name, items, totalMs, capacityMinutes, altCapacityMinutes, compilationMode, coverDataUrl]);

  return (
    <CompilationContext.Provider value={value}>
      {children}
    </CompilationContext.Provider>
  );
};

export const useCompilation = () => {
  const ctx = useContext(CompilationContext);
  if (!ctx) throw new Error('useCompilation must be used within a CompilationProvider');
  return ctx;
};

export default CompilationContext;
