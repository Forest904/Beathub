import React from 'react';
import { useCompilation } from '../context/CompilationContext.jsx';

const CompilationToggle = () => {
  const { compilationMode, toggleCompilationMode, itemCount, totalMs, capacityMinutes, clear, setCompilationMode } = useCompilation();

  const activeClasses = compilationMode
    ? 'border-brand-600 bg-brand-600 text-white hover:bg-brand-700 dark:border-brandDark-500 dark:bg-brandDark-600 dark:hover:bg-brandDark-500'
    : 'border-brand-300 bg-white text-slate-700 hover:bg-brand-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700';

  const capacityMs = Math.max(0, Number(capacityMinutes || 0)) * 60000;
  const overBudget = Number(totalMs || 0) > capacityMs && itemCount > 0;

  const handleClick = () => {
    if (compilationMode && itemCount > 0) {
      // eslint-disable-next-line no-alert
      const ok = window.confirm('Exit Compilation Mode? You can also clear all selected tracks now.\n\nClick OK to clear and exit, or Cancel to keep selections.');
      if (ok) {
        clear();
      }
      setCompilationMode(false);
      return;
    }
    toggleCompilationMode();
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`relative inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm shadow-sm transition ${activeClasses}`}
      aria-pressed={compilationMode}
      aria-label="Toggle Compilation Mode"
      title="Toggle Compilation Mode"
    >
      <span className="font-medium">Compilation</span>
      {itemCount > 0 && (
        <span className={`ml-1 inline-flex min-w-[1.25rem] items-center justify-center rounded-full px-1.5 py-0.5 text-xs font-semibold ${overBudget ? 'bg-brandWarning-500 text-black' : 'bg-brand-500 text-white dark:bg-brandDark-400'}`}>
          {itemCount}
        </span>
      )}
    </button>
  );
};

export default CompilationToggle;
