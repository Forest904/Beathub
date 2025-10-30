import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../shared/hooks/useAuth";
import ThemeToggle from "../shared/components/ThemeToggle.jsx";
import { useSettingsStatus } from "../shared/context/SettingsStatusContext.jsx";
import { fetchDownloadSettings, fetchSettingsStatus, updateDownloadSettings } from "../api";
import AccountSettingsSection from "./settings/components/AccountSettingsSection.jsx";
import DownloadSettingsSection from "./settings/components/DownloadSettingsSection.jsx";
import ApiKeysSection from "./settings/components/ApiKeysSection.jsx";
import { useAccountSettings } from "./settings/hooks/useAccountSettings.js";
import { useDownloadAndApiSettings } from "./settings/hooks/useDownloadAndApiSettings.js";
import { useSettingsSections } from "./settings/hooks/useSettingsSections.js";

const SettingsPage = () => {
  const { user, updateProfile, changeEmail, changePassword } = useAuth();
  const location = useLocation();
  const {
    refresh: refreshSettingsStatus,
    credentialsReady: globalCredentialsReady,
    spotdlReady: globalSpotdlReady,
    loading: settingsLoading,
  } = useSettingsStatus();

  const account = useAccountSettings({ user, updateProfile, changeEmail, changePassword });
  const { sectionsOpen, toggleSection } = useSettingsSections({
    userId: user?.id,
    focusTarget: location?.state?.focus,
    shouldOpenApiKeys: Boolean(!globalCredentialsReady && !settingsLoading),
  });

  const { download, apiKeys, spotdlStatus } = useDownloadAndApiSettings({
    user,
    settingsLoading,
    globalSpotdlReady,
    globalCredentialsReady,
    refreshSettingsStatus,
    fetchDownloadSettingsFn: fetchDownloadSettings,
    fetchSettingsStatusFn: fetchSettingsStatus,
    updateDownloadSettingsFn: updateDownloadSettings,
  });

  if (!user) {
    return (
      <section className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-4 py-16 text-center">
        <div className="rounded-3xl border border-slate-200 bg-white/80 p-10 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">Settings</h1>
          <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">You need to be signed in to view account details.</p>
          <div className="mt-6 flex items-center justify-center gap-4">
            <Link
              to="/login"
              className="rounded-full bg-brand-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-brand-500 dark:bg-brandDark-400 dark:hover:bg-brandDark-300"
            >
              Sign in
            </Link>
            <Link
              to="/register"
              className="rounded-full border border-slate-200 px-5 py-2 text-sm font-semibold text-slate-700 transition hover:border-brand-400 hover:text-brand-600 dark:border-slate-700 dark:text-slate-200 dark:hover:border-brandDark-300 dark:hover:text-brandDark-200"
            >
              Create account
            </Link>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-8 px-4 py-12 md:px-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">Settings</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Manage your personal details. More customization options are coming soon.
          </p>
        </div>
        <div className="mt-2 flex self-end md:mt-0 md:self-start">
          <ThemeToggle />
        </div>
      </header>

      {!globalCredentialsReady && (
        <div className="mb-6 rounded-3xl border border-amber-300 bg-amber-50 p-6 text-sm text-amber-700 dark:border-amber-600/60 dark:bg-amber-900/40 dark:text-amber-200">
          <p>Spotify API keys are not configured. Add your credentials below to enable browsing and downloading features.</p>
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-1">
        <AccountSettingsSection
          sectionsOpen={sectionsOpen}
          toggleSection={toggleSection}
          profile={account.profile}
          email={account.email}
          password={account.password}
          userEmail={user.email ?? ""}
        />

        <div className="space-y-6">
          <DownloadSettingsSection
            sectionsOpen={sectionsOpen}
            toggleSection={toggleSection}
            download={download}
            spotdlStatus={spotdlStatus}
          />
          <ApiKeysSection sectionsOpen={sectionsOpen} toggleSection={toggleSection} apiKeys={apiKeys} />
        </div>
      </div>

      <section className="rounded-3xl border border-dashed border-slate-200 bg-white/60 p-6 text-center text-sm text-slate-400 dark:border-slate-800 dark:bg-slate-900/60 dark:text-slate-500">
        User avatars, theme presets, and profile customization will live here soon. Stay tuned!
      </section>
    </section>
  );
};

export default SettingsPage;
