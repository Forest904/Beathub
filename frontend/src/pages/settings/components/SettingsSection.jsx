import React from "react";

const SectionHeader = ({ id, title, subtitle, isOpen, onToggle }) => (
  <button
    type="button"
    onClick={() => onToggle(id)}
    className="flex w-full items-center justify-between rounded-2xl bg-slate-100/60 px-4 py-3 text-left transition hover:bg-slate-100 dark:bg-slate-800/60 dark:hover:bg-slate-800"
    aria-expanded={isOpen}
  >
    <div>
      <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">{title}</h2>
      {subtitle ? (
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400 dark:text-slate-500">{subtitle}</p>
      ) : null}
    </div>
    <svg
      className={`h-5 w-5 text-slate-500 transition-transform dark:text-slate-300 ${isOpen ? "rotate-180" : ""}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M6 9l6 6 6-6" />
    </svg>
  </button>
);

const SettingsSection = ({ id, title, subtitle, isOpen, onToggle, children }) => (
  <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm transition dark:border-slate-800 dark:bg-slate-900/80">
    <SectionHeader id={id} title={title} subtitle={subtitle} isOpen={isOpen} onToggle={onToggle} />
    <div className={`mt-5 ${isOpen ? "" : "hidden"}`} aria-hidden={!isOpen}>
      {children}
    </div>
  </section>
);

export default SettingsSection;
