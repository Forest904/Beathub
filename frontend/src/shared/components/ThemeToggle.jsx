import React, { useCallback, useMemo } from "react";
import { useTheme } from "../../theme/ThemeContext";

const VinylIcon = ({ active }) => (
  <svg
    aria-hidden="true"
    className={`h-5 w-5 transition-colors ${active ? "text-slate-800" : "text-slate-400 dark:text-slate-500"}`}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.25"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="8.75" />
    <circle cx="12" cy="12" r="2.5" />
    <path d="M19 5.5 21 7.5" />
    <path d="M20 6.5v6" />
  </svg>
);

const SunIcon = () => (
  <svg
    aria-hidden="true"
    className="h-3.5 w-3.5 text-amber-500"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="4" />
    <path d="M12 3v2" />
    <path d="M12 19v2" />
    <path d="M3 12h2" />
    <path d="M19 12h2" />
    <path d="m5.6 5.6 1.4 1.4" />
    <path d="m17 17 1.4 1.4" />
    <path d="m5.6 18.4 1.4-1.4" />
    <path d="m17 7 1.4-1.4" />
  </svg>
);

const MoonIcon = () => (
  <svg
    aria-hidden="true"
    className="h-3.5 w-3.5 text-indigo-300"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" />
  </svg>
);

const ThemeToggle = () => {
  const { theme, setTheme } = useTheme();
  const isDark = theme === "dark";

  const toggle = useCallback(() => {
    setTheme(isDark ? "light" : "dark");
  }, [isDark, setTheme]);

  const positionClass = useMemo(() => (isDark ? "translate-x-6" : "translate-x-0"), [isDark]);

  return (
    <button
      type="button"
      onClick={toggle}
      className="group relative inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.2em] shadow-sm transition hover:shadow dark:border-slate-700 dark:bg-slate-900"
      aria-label="Toggle theme"
      title="Toggle theme"
    >
      <span className="relative flex h-7 w-[3.5rem] items-center rounded-full bg-slate-100 px-2 transition-colors dark:bg-slate-800">
        <span
          className={`flex h-5 w-5 items-center justify-center rounded-full bg-white shadow-sm transition-transform duration-200 ease-out dark:bg-slate-900 ${positionClass}`}
        >
          <VinylIcon active={isDark} />
        </span>
      </span>
      <span className="hidden items-center gap-1 text-slate-500 dark:text-slate-300 sm:inline-flex">
        {isDark ? <MoonIcon /> : <SunIcon />}
      </span>
    </button>
  );
};

export default ThemeToggle;
