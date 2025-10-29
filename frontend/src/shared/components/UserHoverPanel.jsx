import React, { useState, useCallback, useRef, useEffect } from "react";
import { Link } from "react-router-dom";

const UserHoverPanel = ({ email, onLogout }) => {
  const [open, setOpen] = useState(false);
  const closeTimerRef = useRef(null);

  const cancelScheduledClose = useCallback(() => {
    if (closeTimerRef.current) {
      clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
  }, []);

  const openPanel = useCallback(() => {
    cancelScheduledClose();
    setOpen(true);
  }, [cancelScheduledClose]);

  const closePanel = useCallback(() => {
    cancelScheduledClose();
    closeTimerRef.current = setTimeout(() => {
      setOpen(false);
      closeTimerRef.current = null;
    }, 150);
  }, [cancelScheduledClose]);

  const closeNow = useCallback(() => {
    cancelScheduledClose();
    setOpen(false);
  }, [cancelScheduledClose]);

  const handleBlur = useCallback(
    (event) => {
      if (!event.currentTarget.contains(event.relatedTarget)) {
        closeNow();
      }
    },
    [closeNow]
  );

  useEffect(() => () => cancelScheduledClose(), [cancelScheduledClose]);

  const emailDisplay = email || "Unknown";
  const emailInitial = emailDisplay.charAt(0).toUpperCase() || "?";

  return (
    <div
      className="relative hidden text-sm font-medium text-slate-600 dark:text-slate-200 sm:flex"
      onMouseEnter={openPanel}
      onMouseLeave={closePanel}
      onFocusCapture={openPanel}
      onBlur={handleBlur}
    >
      <button
        type="button"
        className="inline-flex items-center gap-2 rounded-full bg-white/60 px-3 py-1 shadow-sm ring-1 ring-slate-200 transition hover:bg-white hover:text-slate-900 dark:bg-slate-800/60 dark:ring-slate-600 dark:hover:bg-slate-800 dark:hover:text-white"
        aria-haspopup="true"
        aria-expanded={open}
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white transition-colors dark:bg-white dark:text-slate-900">
          {emailInitial}
        </span>
        <svg
          className="h-3 w-3 text-slate-400 transition dark:text-slate-500"
          viewBox="0 0 12 8"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path d="M1 1.75 6 6.25 11 1.75" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>

      {open && (
        <div
          className="absolute right-0 top-full z-30 mt-3 min-w-[240px] rounded-2xl border border-slate-200 bg-white/95 p-4 text-left shadow-lg shadow-slate-600/10 backdrop-blur dark:border-slate-700 dark:bg-slate-900/95 dark:shadow-slate-950/40"
          onMouseEnter={openPanel}
          onMouseLeave={closePanel}
        >
          <div className="flex w-full flex-col gap-3">
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-left text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">You've signed in as:</p>
              <p className="mt-1 break-words text-sm font-semibold text-slate-700 dark:text-slate-100">{emailDisplay}</p>
            </div>
            <div className="flex flex-col gap-2 text-sm font-semibold text-slate-600 dark:text-slate-200">
              <Link
                to="/playlists"
                onClick={closeNow}
                className="rounded-full bg-slate-100 px-3 py-2 text-center transition hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700"
              >
                My Playlists
              </Link>
              <Link
                to="/favorites"
                onClick={closeNow}
                className="rounded-full bg-slate-100 px-3 py-2 text-center transition hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700"
              >
                Favourites
              </Link>
              <Link
                to="/settings"
                onClick={closeNow}
                className="rounded-full bg-slate-900 px-3 py-2 text-center text-white transition hover:bg-slate-700 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100"
              >
                Settings
              </Link>
            </div>
            <button
              type="button"
              onClick={() => {
                closeNow();
                onLogout();
              }}
              className="inline-flex items-center justify-center gap-2 rounded-full bg-gradient-to-r from-brand-500 to-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:from-brand-500/90 hover:to-brand-600/90 focus:outline-none focus-visible:ring focus-visible:ring-brand-400 dark:from-brandDark-400 dark:to-brandDark-500 dark:hover:from-brandDark-400/90 dark:hover:to-brandDark-500/90"
            >
              Logout
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserHoverPanel;
