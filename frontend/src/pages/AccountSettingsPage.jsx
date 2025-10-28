import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../shared/hooks/useAuth";
import { fetchDownloadSettings, fetchSettingsStatus, updateDownloadSettings } from "../api";

const deriveUsername = (user) => {
  if (!user) return "";
  if (user.username && typeof user.username === "string" && user.username.trim().length > 0) {
    return user.username.trim();
  }
  if (user.email && typeof user.email === "string") {
    const prefix = user.email.split("@")[0];
    return prefix || user.email;
  }
  return "";
};

const formatErrors = (errors) => {
  if (!errors) return "";
  if (typeof errors === "string") return errors;
  if (Array.isArray(errors)) return errors.join(" ");
  return Object.values(errors)
    .flat()
    .join(" ");
};

const DOWNLOAD_SETTINGS_STORAGE_KEY = "download-settings:v1";
const THREADS_DEFAULT = 6;

const DEFAULT_DOWNLOAD_SETTINGS = {
  base_output_dir: "./downloads",
  threads: THREADS_DEFAULT,
  preload: true,
};

const clampThreads = (value) => {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return 1;
  }
  return Math.min(12, Math.max(1, Math.round(numeric)));
};

const useAutoDismiss = (status, setter, delay = 3000) => {
  useEffect(() => {
    if (!status || status.type === "pending") return undefined;
    const timer = setTimeout(() => setter(null), delay);
    return () => clearTimeout(timer);
  }, [status, setter, delay]);
};

const AccountSettingsPage = () => {
  const { user, updateProfile, changeEmail, changePassword } = useAuth();

  const initialProfile = useMemo(
    () => ({
      username: deriveUsername(user),
      displayName: user?.display_name ?? "",
      avatarUrl: user?.avatar_url ?? "",
    }),
    [user]
  );

  const [profileForm, setProfileForm] = useState(initialProfile);
  const [profileStatus, setProfileStatus] = useState(null);

  const [emailForm, setEmailForm] = useState({ newEmail: user?.email ?? "", currentPassword: "" });
  const [emailStatus, setEmailStatus] = useState(null);

  const [passwordForm, setPasswordForm] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [passwordStatus, setPasswordStatus] = useState(null);

  const [downloadSettings, setDownloadSettings] = useState(DEFAULT_DOWNLOAD_SETTINGS);
  const [downloadDefaults, setDownloadDefaults] = useState(DEFAULT_DOWNLOAD_SETTINGS);
  const [downloadStatus, setDownloadStatus] = useState(null);
  const [downloadLoading, setDownloadLoading] = useState(true);
  const downloadHydratedRef = useRef(false);
  const [spotdlStatus, setSpotdlStatus] = useState({ ready: false, loading: true });

  const [sectionsOpen, setSectionsOpen] = useState({
    profile: false,
    downloads: false,
    email: false,
    password: false,
  });

  useEffect(() => {
    setProfileForm(initialProfile);
  }, [initialProfile]);

  useEffect(() => {
    setEmailForm((prev) => ({ ...prev, newEmail: user?.email ?? "" }));
  }, [user?.email]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(DOWNLOAD_SETTINGS_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === "object") {
          const next = { ...parsed };
          if (typeof next.threads !== "undefined") {
            next.threads = clampThreads(next.threads);
          }
          if (typeof next.preload !== "undefined") {
            next.preload = Boolean(next.preload);
          }
          setDownloadSettings((prev) => ({
            ...prev,
            ...next,
          }));
        }
      }
    } catch (error) {
      // eslint-disable-next-line no-console
      console.warn("Failed to load download settings from storage", error);
    } finally {
      downloadHydratedRef.current = true;
    }
  }, []);

  useEffect(() => {
    if (!downloadHydratedRef.current) return;
    try {
      window.localStorage.setItem(DOWNLOAD_SETTINGS_STORAGE_KEY, JSON.stringify(downloadSettings));
    } catch (error) {
      // eslint-disable-next-line no-console
      console.warn("Failed to persist download settings", error);
    }
  }, [downloadSettings]);

  useEffect(() => {
    let cancelled = false;

    if (!user) {
      setDownloadLoading(false);
      return () => {
        cancelled = true;
      };
    }

    const loadSettings = async () => {
      setDownloadLoading(true);
      try {
        const [settingsResponse, statusResponse] = await Promise.all([
          fetchDownloadSettings(),
          fetchSettingsStatus().catch(() => ({ spotdl_ready: false })),
        ]);
        if (cancelled) {
          return;
        }
        const defaults = { ...DEFAULT_DOWNLOAD_SETTINGS, ...(settingsResponse?.defaults || {}) };
        const settings = { ...defaults, ...(settingsResponse?.settings || {}) };
        const normalizedDefaults = {
          ...defaults,
          threads: clampThreads(defaults.threads),
          preload: Boolean(defaults.preload),
        };
        const normalizedSettings = {
          ...settings,
          threads: clampThreads(settings.threads),
          preload: Boolean(settings.preload),
        };
        setDownloadDefaults(normalizedDefaults);
        setDownloadSettings(normalizedSettings);
        setSpotdlStatus({ ready: Boolean(statusResponse?.spotdl_ready), loading: false });
        setDownloadStatus(null);
        if (downloadHydratedRef.current) {
          try {
            window.localStorage.setItem(DOWNLOAD_SETTINGS_STORAGE_KEY, JSON.stringify(normalizedSettings));
          } catch (error) {
            // eslint-disable-next-line no-console
            console.warn("Failed to persist download settings", error);
          }
        }
      } catch (error) {
        if (!cancelled) {
          setDownloadStatus({ type: "error", message: "Unable to load download settings." });
          setSpotdlStatus({ ready: false, loading: false });
        }
      } finally {
        if (!cancelled) {
          setDownloadLoading(false);
        }
      }
    };

    loadSettings();

    return () => {
      cancelled = true;
    };
  }, [user]);

  const toggleSection = useCallback((key) => {
    setSectionsOpen((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const handleProfileChange = useCallback((event) => {
    const { name, value } = event.target;
    setProfileForm((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleProfileSubmit = useCallback(
    async (event) => {
      event.preventDefault();
      setProfileStatus({ type: "pending" });
      const payload = {
        username: profileForm.username.trim(),
        display_name: profileForm.displayName.trim(),
        avatar_url: profileForm.avatarUrl.trim(),
      };
      const result = await updateProfile(payload);
      if (result.ok) {
        setProfileStatus({ type: "success", message: "Profile updated successfully." });
      } else {
        setProfileStatus({ type: "error", message: formatErrors(result.errors) || "Unable to update profile." });
      }
    },
    [profileForm, updateProfile]
  );

  const handleEmailChange = useCallback((event) => {
    const { name, value } = event.target;
    setEmailForm((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleEmailSubmit = useCallback(
    async (event) => {
      event.preventDefault();
      setEmailStatus({ type: "pending" });
      const result = await changeEmail({
        newEmail: emailForm.newEmail.trim().toLowerCase(),
        currentPassword: emailForm.currentPassword,
      });
      if (result.ok) {
        setEmailStatus({ type: "success", message: "Email updated." });
        setEmailForm({ newEmail: result.user?.email ?? "", currentPassword: "" });
      } else {
        setEmailStatus({ type: "error", message: formatErrors(result.errors) || "Unable to update email." });
      }
    },
    [changeEmail, emailForm]
  );

  const handlePasswordChange = useCallback((event) => {
    const { name, value } = event.target;
    setPasswordForm((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handlePasswordSubmit = useCallback(
    async (event) => {
      event.preventDefault();
      setPasswordStatus({ type: "pending" });
      if (passwordForm.newPassword !== passwordForm.confirmPassword) {
        setPasswordStatus({ type: "error", message: "Passwords do not match." });
        return;
      }
      const result = await changePassword(passwordForm);
      if (result.ok) {
        setPasswordStatus({ type: "success", message: "Password updated." });
        setPasswordForm({ currentPassword: "", newPassword: "", confirmPassword: "" });
      } else {
        setPasswordStatus({ type: "error", message: formatErrors(result.errors) || "Unable to update password." });
      }
    },
    [changePassword, passwordForm]
  );

  const handleDownloadChange = useCallback((event) => {
    const { name, value, type, checked } = event.target;
    setDownloadSettings((prev) => {
      if (name === "threads") {
        const numeric = Number(value);
        if (Number.isNaN(numeric)) {
          return prev;
        }
        const bounded = clampThreads(numeric);
        return { ...prev, threads: bounded };
      }
      if (name === "preload") {
        return { ...prev, preload: type === "checkbox" ? checked : Boolean(value) };
      }
      return { ...prev, [name]: value };
    });
    setDownloadStatus(null);
  }, []);

  const handleDownloadSubmit = useCallback(
    async (event) => {
      event.preventDefault();
      setDownloadStatus({ type: "pending" });

      const trimmedDir = (downloadSettings.base_output_dir || "").trim();
      const baseOutputDir = trimmedDir || downloadDefaults.base_output_dir;
      const numericThreads = Number(downloadSettings.threads);
      const threads = Number.isNaN(numericThreads)
        ? clampThreads(THREADS_DEFAULT)
        : clampThreads(numericThreads);
      const payload = {
        base_output_dir: baseOutputDir,
        threads,
        preload: Boolean(downloadSettings.preload),
      };

      try {
        const response = await updateDownloadSettings(payload);
        const defaults = { ...DEFAULT_DOWNLOAD_SETTINGS, ...(response?.defaults || {}) };
        const settings = { ...defaults, ...(response?.settings || payload) };
        setDownloadDefaults(defaults);
        setDownloadSettings(settings);
        setSpotdlStatus({ ready: true, loading: false });
        setDownloadStatus({ type: "success", message: "Download settings updated." });
      } catch (error) {
        const message =
          formatErrors(error?.details || error?.response?.data?.errors) || "Unable to update download settings.";
        setDownloadStatus({ type: "error", message });
        setSpotdlStatus({ ready: false, loading: false });
      }
    },
    [downloadDefaults, downloadSettings]
  );

  useAutoDismiss(profileStatus, setProfileStatus);
  useAutoDismiss(emailStatus, setEmailStatus);
  useAutoDismiss(passwordStatus, setPasswordStatus);
  useAutoDismiss(downloadStatus, setDownloadStatus);

  useEffect(() => {
    (async () => {
      try {
        const status = await fetchSettingsStatus();
        setSpotdlStatus({ ready: Boolean(status?.spotdl_ready), loading: false });
      } catch (error) {
        setSpotdlStatus((prev) => ({ ...prev, loading: false }));
      }
    })();
  }, []);

  if (!user) {
    return (
      <section className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-4 py-16 text-center">
        <div className="rounded-3xl border border-slate-200 bg-white/80 p-10 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">Account Settings</h1>
          <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
            You need to be signed in to view account details.
          </p>
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

  const renderStatus = (status) => {
    if (!status || status.type === "pending") {
      return status?.type === "pending" ? (
        <p className="text-xs text-slate-400 dark:text-slate-500">Working on it...</p>
      ) : null;
    }
    if (status.type === "success") {
      return <p className="text-xs font-medium text-emerald-500">{status.message}</p>;
    }
    if (status.type === "error") {
      return <p className="text-xs font-medium text-rose-500">{status.message}</p>;
    }
    return null;
  };

  const SectionHeader = ({ id, title, subtitle, isOpen }) => (
    <button
      type="button"
      onClick={() => toggleSection(id)}
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

  return (
    <section className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-8 px-4 py-12 md:px-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">Account Settings</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Manage your personal details. More customization options are coming soon.
        </p>
      </header>

      <div className="grid gap-6 md:grid-cols-1">
        <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm transition dark:border-slate-800 dark:bg-slate-900/80">
          <SectionHeader id="profile" title="Profile" subtitle="Basic details" isOpen={sectionsOpen.profile} />
          {sectionsOpen.profile && (
            <form className="mt-5 space-y-5" onSubmit={handleProfileSubmit}>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="flex flex-col gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
                  Username
                  <input
                    type="text"
                    name="username"
                    value={profileForm.username}
                    onChange={handleProfileChange}
                    className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm transition focus:border-brand-400 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                    placeholder="Your username"
                  />
                </label>
                <label className="flex flex-col gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
                  Display name
                  <input
                    type="text"
                    name="displayName"
                    value={profileForm.displayName}
                    onChange={handleProfileChange}
                    className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm transition focus:border-brand-400 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                    placeholder="How others see you"
                  />
                </label>
              </div>

              <label className="flex flex-col gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
                Avatar URL
                <input
                  type="url"
                  name="avatarUrl"
                  value={profileForm.avatarUrl}
                  onChange={handleProfileChange}
                  className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm transition focus:border-brand-400 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                  placeholder="https://example.com/avatar.png"
                />
              </label>

              <div className="flex items-center justify-between">
                {renderStatus(profileStatus)}
                <button
                  type="submit"
                  className="rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100"
                >
                  Save changes
                </button>
              </div>
            </form>
          )}
        </section>

        <section className="space-y-6">
          <div className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm transition dark:border-slate-800 dark:bg-slate-900/80">
            <SectionHeader id="downloads" title="Download Settings" subtitle="SpotDL preferences" isOpen={sectionsOpen.downloads} />
            {sectionsOpen.downloads && (
              <form className="mt-5 space-y-5" onSubmit={handleDownloadSubmit}>
                <label className="flex flex-col gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
                  Base output directory
                  <input
                    type="text"
                    name="base_output_dir"
                    value={downloadSettings.base_output_dir}
                    onChange={handleDownloadChange}
                    className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm transition focus:border-brand-400 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                    placeholder={downloadDefaults.base_output_dir}
                    disabled={downloadLoading || downloadStatus?.type === "pending"}
                  />
                  <span className="text-xs text-slate-400 dark:text-slate-500">Default: {downloadDefaults.base_output_dir}</span>
                </label>

                <div className="grid gap-4 md:grid-cols-2">
                  <label className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 text-sm font-medium text-slate-600 shadow-sm transition focus-within:border-brand-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                    <div className="flex items-center justify-between gap-3">
                      <span>SpotDL threads</span>
                      <span className="w-10 text-right text-xs font-semibold text-slate-600 dark:text-slate-200">{downloadSettings.threads}</span>
                    </div>
                    <input
                      type="range"
                      min={1}
                      max={12}
                      step={1}
                      name="threads"
                      value={downloadSettings.threads}
                      onChange={handleDownloadChange}
                      className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-brand-600 transition disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-700 dark:accent-brandDark-400"
                      disabled={downloadLoading || downloadStatus?.type === "pending"}
                      aria-valuemin={1}
                      aria-valuemax={12}
                      aria-valuenow={downloadSettings.threads}
                    />
                    <span className="text-xs text-slate-400 dark:text-slate-500">Default: {THREADS_DEFAULT}</span>
                  </label>

                  <label className="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-600 shadow-sm transition focus-within:border-brand-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                    <span className="flex flex-col">
                      <span>Preload songs</span>
                      <span className="text-xs text-slate-400 dark:text-slate-500">Prepare URLs ahead of downloads for faster batches.</span>
                    </span>
                    <input
                      type="checkbox"
                      name="preload"
                      checked={Boolean(downloadSettings.preload)}
                      onChange={handleDownloadChange}
                      className="h-5 w-5 rounded border-slate-300 text-brand-600 focus:ring-brand-500 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-600 dark:bg-slate-700"
                      disabled={downloadLoading || downloadStatus?.type === "pending"}
                    />
                  </label>
                </div>

                <p className="text-xs text-slate-400 dark:text-slate-500">
                  Changes apply to new downloads. Jobs already in progress continue with their current configuration.
                </p>

                <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:gap-3">
                  <div className="flex items-center gap-3">
                    <button
                      type="submit"
                      className="rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-brandDark-400 dark:hover:bg-brandDark-300"
                      disabled={downloadLoading || downloadStatus?.type === "pending"}
                    >
                      Save download settings
                    </button>
                    {spotdlStatus.ready ? (
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
                  <div className="min-h-[1rem] text-sm text-slate-500 dark:text-slate-400">
                    {renderStatus(downloadStatus)}
                  </div>
                </div>
              </form>
            )}
          </div>
          <div className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm transition dark:border-slate-800 dark:bg-slate-900/80">
            <SectionHeader id="email" title="Email" subtitle={`Current: ${user.email}`} isOpen={sectionsOpen.email} />
            {sectionsOpen.email && (
              <form className="mt-5 space-y-4" onSubmit={handleEmailSubmit}>
                <label className="flex flex-col gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
                  New email
                  <input
                    type="email"
                    name="newEmail"
                    value={emailForm.newEmail}
                    onChange={handleEmailChange}
                    className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm transition focus:border-brand-400 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                    placeholder="new@email.com"
                    required
                  />
                </label>

                <label className="flex flex-col gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
                  Current password
                  <input
                    type="password"
                    name="currentPassword"
                    value={emailForm.currentPassword}
                    onChange={handleEmailChange}
                    className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm transition focus:border-brand-400 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                    placeholder="Enter password"
                    required
                  />
                </label>

                <div className="flex items-center justify-between">
                  {renderStatus(emailStatus)}
                  <button
                    type="submit"
                    className="rounded-full bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-500 dark:bg-brandDark-400 dark:hover:bg-brandDark-300"
                  >
                    Update email
                  </button>
                </div>
              </form>
            )}
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm transition dark:border-slate-800 dark:bg-slate-900/80">
            <SectionHeader id="password" title="Password" subtitle="Security" isOpen={sectionsOpen.password} />
            {sectionsOpen.password && (
              <form className="mt-5 space-y-4" onSubmit={handlePasswordSubmit}>
                <label className="flex flex-col gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
                  Current password
                  <input
                    type="password"
                    name="currentPassword"
                    value={passwordForm.currentPassword}
                    onChange={handlePasswordChange}
                    className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm transition focus:border-brand-400 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                    placeholder="Enter current password"
                    required
                  />
                </label>

                <label className="flex flex-col gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
                  New password
                  <input
                    type="password"
                    name="newPassword"
                    value={passwordForm.newPassword}
                    onChange={handlePasswordChange}
                    className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm transition focus-border-brand-400 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                    placeholder="At least 8 characters"
                    required
                  />
                </label>

                <label className="flex flex-col gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
                  Confirm new password
                  <input
                    type="password"
                    name="confirmPassword"
                    value={passwordForm.confirmPassword}
                    onChange={handlePasswordChange}
                    className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 shadow-sm transition focus:border-brand-400 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                    placeholder="Repeat new password"
                    required
                  />
                </label>

                <div className="flex items-center justify-between">
                  {renderStatus(passwordStatus)}
                  <button
                    type="submit"
                    className="rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100"
                  >
                    Update password
                  </button>
                </div>
              </form>
            )}
          </div>

          <section className="rounded-3xl border border-dashed border-slate-200 bg-white/60 p-6 text-center text-sm text-slate-400 dark:border-slate-800 dark:bg-slate-900/60 dark:text-slate-500">
            User avatars, theme presets, and profile customization will live here soon. Stay tuned!
          </section>
        </section>
      </div>
    </section>
  );
};

export default AccountSettingsPage;




