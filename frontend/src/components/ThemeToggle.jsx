import React from 'react';
import { useTheme } from '../theme/ThemeContext';

const ThemeToggle = () => {
  const { theme, toggle } = useTheme();

  return (
    <button
      type="button"
      onClick={toggle}
      className="inline-flex items-center gap-2 rounded-full border border-brand-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm transition hover:bg-brand-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
      aria-label="Toggle theme"
      title="Toggle theme"
    >
      <span aria-hidden className="text-base leading-none">
        {theme === 'dark' ? '🌙' : '☀️'}
      </span>
      <span className="hidden sm:inline">{theme === 'dark' ? 'Dark' : 'Light'}</span>
    </button>
  );
};

export default ThemeToggle;
