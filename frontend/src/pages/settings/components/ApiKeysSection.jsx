import React from "react";
import { API_KEY_FIELDS } from "../constants.js";
import SettingsSection from "./SettingsSection.jsx";
import StatusMessage from "./StatusMessage.jsx";

const ApiKeysSection = ({ sectionsOpen, toggleSection, apiKeys }) => (
  <SettingsSection
    id="apiKeys"
    title="API Keys"
    subtitle="Integrations"
    isOpen={sectionsOpen.apiKeys}
    onToggle={toggleSection}
  >
    <form className="space-y-5" onSubmit={apiKeys.onSubmit}>
      {API_KEY_FIELDS.map(({ key, label, helper, link, linkLabel }) => {
        const stored = apiKeys.meta[key]?.stored;
        const preview = apiKeys.meta[key]?.preview;
        const pendingClear = apiKeys.clearState[key];
        return (
          <div key={key} className="space-y-2">
            <label className="flex flex-col gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
              {label}
              <input
                type="password"
                name={key}
                value={apiKeys.form[key]}
                onChange={apiKeys.onChange}
                className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm transition focus:border-brand-400 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                placeholder={stored ? "Saved value hidden" : "Enter key"}
                autoComplete="off"
                disabled={apiKeys.status?.type === "pending"}
              />
            </label>
            <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500 dark:text-slate-400">
              <span>
                {helper}{" "}
                <a
                  href={link}
                  target="_blank"
                  rel="noreferrer"
                  className="font-semibold text-brand-600 hover:underline dark:text-brandDark-300"
                >
                  {linkLabel}
                </a>
              </span>
              <div className="flex items-center gap-3">
                {stored ? (
                  <span className="font-mono text-[11px] text-slate-400 dark:text-slate-500">
                    Stored ({preview || "****"})
                    {pendingClear ? " - will be removed" : ""}
                  </span>
                ) : (
                  <span className="text-[11px] uppercase tracking-[0.2em] text-slate-400">Not set</span>
                )}
                {stored ? (
                  <button
                    type="button"
                    onClick={() => apiKeys.onClear(key)}
                    className="text-xs font-semibold text-slate-500 transition hover:text-rose-500 disabled:cursor-not-allowed dark:text-slate-400 dark:hover:text-rose-400"
                    disabled={apiKeys.status?.type === "pending"}
                  >
                    Clear
                  </button>
                ) : null}
              </div>
            </div>
          </div>
        );
      })}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex flex-1 justify-start">
          <StatusMessage status={apiKeys.status} />
        </div>
        <div className="flex flex-1 justify-end">
          <button
            type="submit"
            className="rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-brandDark-400 dark:hover:bg-brandDark-300"
            disabled={apiKeys.status?.type === "pending"}
          >
            Save API keys
          </button>
        </div>
      </div>
    </form>
  </SettingsSection>
);

export default ApiKeysSection;

