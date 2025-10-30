import React from "react";
import SettingsSection from "./SettingsSection.jsx";
import StatusMessage from "./StatusMessage.jsx";

const DownloadSettingsSection = ({ sectionsOpen, toggleSection, download, spotdlStatus }) => (
  <SettingsSection
    id="downloads"
    title="Download Settings"
    subtitle="SpotDL preferences"
    isOpen={sectionsOpen.downloads}
    onToggle={toggleSection}
  >
    <form className="space-y-5" onSubmit={download.onSubmit}>
      <label className="flex flex-col gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
        Base output directory
        <input
          type="text"
          name="base_output_dir"
          value={download.settings.base_output_dir}
          onChange={download.onChange}
          className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm transition focus:border-brand-400 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          placeholder={download.defaults.base_output_dir}
          disabled={download.loading || download.status?.type === "pending"}
        />
        <span className="text-xs text-slate-400 dark:text-slate-500">Default: {download.defaults.base_output_dir}</span>
      </label>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 text-sm font-medium text-slate-600 shadow-sm transition focus-within:border-brand-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
          <div className="flex items-center justify-between gap-3">
            <span>SpotDL threads</span>
            <span className="w-10 text-right text-xs font-semibold text-slate-600 dark:text-slate-200">
              {download.settings.threads}
            </span>
          </div>
          <input
            type="range"
            min={1}
            max={12}
            step={1}
            name="threads"
            value={download.settings.threads}
            onChange={download.onChange}
            className="accent-brand-500 dark:accent-brandDark-300"
            disabled={download.loading || download.status?.type === "pending"}
          />
          <span className="text-xs text-slate-400 dark:text-slate-500">
            Increase the number of concurrent downloads. Higher values may be unstable on slower devices.
          </span>
        </label>

        <label className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 text-sm font-medium text-slate-600 shadow-sm transition focus-within:border-brand-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
          <div className="flex items-center justify-between gap-3">
            <span>Preload tracks</span>
            <div className="relative inline-flex items-center">
              <input
                type="checkbox"
                name="preload"
                checked={Boolean(download.settings.preload)}
                onChange={download.onChange}
                className="peer h-5 w-10 cursor-pointer appearance-none rounded-full border border-slate-200 bg-slate-200 transition checked:border-brand-500 checked:bg-brand-500 focus:outline-none dark:border-slate-700 dark:bg-slate-700 dark:checked:border-brandDark-300 dark:checked:bg-brandDark-300"
                disabled={download.loading || download.status?.type === "pending"}
              />
              <span className="pointer-events-none absolute left-1 top-1 h-3 w-3 rounded-full bg-white transition peer-checked:translate-x-5" />
            </div>
          </div>
          <span className="text-xs text-slate-400 dark:text-slate-500">
            Preload metadata before downloading for more reliable tagging.
          </span>
        </label>
      </div>

      <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 text-xs text-slate-500 shadow-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
        <p className="font-semibold text-slate-600 dark:text-slate-200">SpotDL status</p>
        {spotdlStatus.loading ? (
          <p>Checking SpotDL status&hellip;</p>
        ) : spotdlStatus.ready ? (
          <p>SpotDL is ready to go. Happy downloading!</p>
        ) : (
          <p>SpotDL is not ready. Double-check your credentials and download directory.</p>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex flex-1 justify-start">
          <StatusMessage status={download.status} />
        </div>
        <div className="flex flex-1 justify-center">
          {spotdlStatus.ready && !spotdlStatus.loading ? (
            <span className="flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-600 dark:border-emerald-900/60 dark:bg-emerald-900/30 dark:text-emerald-300">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
              </svg>
              SpotDL working!
            </span>
          ) : null}
        </div>
        <div className="flex flex-1 justify-end">
          <button
            type="submit"
            className="rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-brandDark-400 dark:hover:bg-brandDark-300"
            disabled={download.loading || download.status?.type === "pending"}
          >
            Save download settings
          </button>
        </div>
      </div>
    </form>
  </SettingsSection>
);

export default DownloadSettingsSection;

