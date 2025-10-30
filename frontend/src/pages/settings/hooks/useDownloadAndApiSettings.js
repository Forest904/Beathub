import { useCallback, useEffect, useRef, useState } from "react";
import {
  API_KEY_FIELDS,
  DEFAULT_DOWNLOAD_SETTINGS,
  DOWNLOAD_SETTINGS_STORAGE_KEY,
  createDefaultApiKeysClearState,
  createDefaultApiKeysMeta,
  createEmptyApiKeysForm,
} from "../constants";
import { clampThreads, formatErrors, normalizeApiKeysMeta } from "../utils";
import { useAutoDismiss } from "./useAutoDismiss";

export const useDownloadAndApiSettings = ({
  user,
  settingsLoading,
  globalSpotdlReady,
  globalCredentialsReady,
  refreshSettingsStatus,
  fetchDownloadSettingsFn,
  fetchSettingsStatusFn,
  updateDownloadSettingsFn,
}) => {
  const [downloadSettings, setDownloadSettings] = useState(DEFAULT_DOWNLOAD_SETTINGS);
  const [downloadDefaults, setDownloadDefaults] = useState(DEFAULT_DOWNLOAD_SETTINGS);
  const [downloadStatus, setDownloadStatus] = useState(null);
  const [downloadLoading, setDownloadLoading] = useState(true);
  const downloadHydratedRef = useRef(false);

  const [spotdlStatus, setSpotdlStatus] = useState({ ready: false, loading: true });

  const [apiKeysForm, setApiKeysForm] = useState(() => createEmptyApiKeysForm());
  const [apiKeysMeta, setApiKeysMeta] = useState(() => createDefaultApiKeysMeta());
  const [apiKeysClearState, setApiKeysClearState] = useState(() => createDefaultApiKeysClearState());
  const [apiKeysStatus, setApiKeysStatus] = useState(null);

  useEffect(() => {
    setSpotdlStatus((prev) => ({
      ready: settingsLoading ? prev.ready : Boolean(globalSpotdlReady),
      loading: settingsLoading,
    }));
  }, [settingsLoading, globalSpotdlReady]);

  useAutoDismiss(downloadStatus, setDownloadStatus);
  useAutoDismiss(apiKeysStatus, setApiKeysStatus);

  useEffect(() => {
    try {
      const raw = typeof window !== "undefined" ? window.localStorage.getItem(DOWNLOAD_SETTINGS_STORAGE_KEY) : null;
      if (!raw) {
        downloadHydratedRef.current = true;
        return;
      }
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        const next = { ...parsed };
        if (typeof next.threads !== "undefined") {
          next.threads = clampThreads(next.threads);
        }
        if (typeof next.preload !== "undefined") {
          next.preload = Boolean(next.preload);
        }
        setDownloadSettings((prev) => ({ ...prev, ...next }));
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
      if (typeof window !== "undefined") {
        window.localStorage.setItem(DOWNLOAD_SETTINGS_STORAGE_KEY, JSON.stringify(downloadSettings));
      }
    } catch (error) {
      // eslint-disable-next-line no-console
      console.warn("Failed to persist download settings", error);
    }
  }, [downloadSettings]);

  const applySettingsResponse = useCallback((response, fallbackDownloadPayload = {}) => {
    const defaults = { ...DEFAULT_DOWNLOAD_SETTINGS, ...(response?.defaults || {}) };
    const settings = { ...defaults, ...(response?.settings || fallbackDownloadPayload || {}) };
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
    setApiKeysMeta(normalizeApiKeysMeta(response?.api_keys, API_KEY_FIELDS, createDefaultApiKeysMeta));
    setApiKeysForm(createEmptyApiKeysForm());
    setApiKeysClearState(createDefaultApiKeysClearState());
    setApiKeysStatus(null);
    const spotdlReady = typeof response?.spotdl_ready === "boolean" ? Boolean(response.spotdl_ready) : undefined;
    const credentialsReady = typeof response?.credentials_ready === "boolean" ? Boolean(response.credentials_ready) : undefined;
    return { normalizedDefaults, normalizedSettings, spotdlReady, credentialsReady };
  }, []);

  useEffect(() => {
    let cancelled = false;

    if (!user) {
      setDownloadLoading(false);
      setSpotdlStatus({ ready: false, loading: false });
      return () => {
        cancelled = true;
      };
    }

    const loadSettings = async () => {
      setDownloadLoading(true);
      try {
        const [settingsResponse, statusResponse] = await Promise.all([
          fetchDownloadSettingsFn(),
          fetchSettingsStatusFn().catch(() => ({ spotdl_ready: false })),
        ]);
        if (cancelled) {
          return;
        }
        const applied = applySettingsResponse(settingsResponse);
        const readyFromSettings = applied?.spotdlReady;
        const readyFromStatus = statusResponse?.spotdl_ready;
        const credentialsFromSettings = applied?.credentialsReady;
        const credentialsFromStatus =
          typeof statusResponse?.credentials_ready === "boolean"
            ? Boolean(statusResponse.credentials_ready)
            : undefined;
        const ready = typeof readyFromSettings === "boolean" ? readyFromSettings : Boolean(readyFromStatus);
        const credentialsReady =
          typeof credentialsFromSettings === "boolean"
            ? credentialsFromSettings
            : typeof credentialsFromStatus === "boolean"
              ? credentialsFromStatus
              : Boolean(statusResponse?.spotify_ready);
        setSpotdlStatus({ ready: ready && credentialsReady, loading: false });
        setDownloadStatus(null);
        refreshSettingsStatus();
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
  }, [
    applySettingsResponse,
    fetchDownloadSettingsFn,
    fetchSettingsStatusFn,
    refreshSettingsStatus,
    user,
  ]);

  const buildDownloadPayload = useCallback(() => {
    const trimmedDir = (downloadSettings.base_output_dir || "").trim();
    const fallbackDir = downloadDefaults.base_output_dir || DEFAULT_DOWNLOAD_SETTINGS.base_output_dir;
    const baseOutputDir = trimmedDir || fallbackDir;
    const numericThreads = Number(downloadSettings.threads);
    const threads = Number.isNaN(numericThreads)
      ? clampThreads(DEFAULT_DOWNLOAD_SETTINGS.threads)
      : clampThreads(numericThreads);
    return {
      base_output_dir: baseOutputDir,
      threads,
      preload: Boolean(downloadSettings.preload),
    };
  }, [downloadDefaults, downloadSettings]);

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

      const downloadPayload = buildDownloadPayload();
      const payload = { download: downloadPayload };

      try {
        const response = await updateDownloadSettingsFn(payload);
        const applied = applySettingsResponse(response, downloadPayload);
        const readyFlag = typeof applied?.spotdlReady === "boolean" ? applied.spotdlReady : globalSpotdlReady;
        const credentialsFlag = typeof applied?.credentialsReady === "boolean" ? applied.credentialsReady : globalCredentialsReady;
        setSpotdlStatus({ ready: Boolean(readyFlag && credentialsFlag), loading: false });
        setDownloadStatus({ type: "success", message: "Download settings updated." });
        refreshSettingsStatus();
      } catch (error) {
        const message =
          formatErrors(error?.details || error?.response?.data?.errors) || "Unable to update download settings.";
        setDownloadStatus({ type: "error", message });
        setSpotdlStatus({ ready: false, loading: false });
      }
    },
    [
      applySettingsResponse,
      buildDownloadPayload,
      globalCredentialsReady,
      globalSpotdlReady,
      refreshSettingsStatus,
      updateDownloadSettingsFn,
    ]
  );

  const handleApiKeyChange = useCallback((event) => {
    const { name, value } = event.target;
    setApiKeysForm((prev) => ({ ...prev, [name]: value }));
    setApiKeysClearState((prev) => ({ ...prev, [name]: false }));
    setApiKeysStatus(null);
  }, []);

  const handleApiKeyClear = useCallback((name) => {
    setApiKeysForm((prev) => ({ ...prev, [name]: "" }));
    setApiKeysClearState((prev) => ({ ...prev, [name]: true }));
    setApiKeysStatus(null);
  }, []);

  const handleApiKeysSubmit = useCallback(
    async (event) => {
      event.preventDefault();
      setApiKeysStatus({ type: "pending" });

      const downloadPayload = buildDownloadPayload();
      const apiPayload = {};

      API_KEY_FIELDS.forEach(({ key }) => {
        const raw = apiKeysForm[key];
        const trimmed = typeof raw === "string" ? raw.trim() : "";
        if (trimmed) {
          apiPayload[key] = trimmed;
        } else if (apiKeysClearState[key]) {
          apiPayload[key] = "";
        }
      });

      const payload = { download: downloadPayload };
      if (Object.keys(apiPayload).length > 0) {
        payload.api_keys = apiPayload;
      }

      try {
        const response = await updateDownloadSettingsFn(payload);
        const applied = applySettingsResponse(response, downloadPayload);
        const readyFlag = typeof applied?.spotdlReady === "boolean" ? applied.spotdlReady : globalSpotdlReady;
        const credentialsFlag = typeof applied?.credentialsReady === "boolean" ? applied.credentialsReady : globalCredentialsReady;
        setApiKeysStatus({ type: "success", message: "API keys updated." });
        setSpotdlStatus({ ready: Boolean(readyFlag && credentialsFlag), loading: false });
        setDownloadStatus(null);
        refreshSettingsStatus();
      } catch (error) {
        const message = formatErrors(error?.details || error?.response?.data?.errors) || "Unable to update API keys.";
        setApiKeysStatus({ type: "error", message });
      }
    },
    [
      apiKeysClearState,
      apiKeysForm,
      applySettingsResponse,
      buildDownloadPayload,
      globalCredentialsReady,
      globalSpotdlReady,
      refreshSettingsStatus,
      updateDownloadSettingsFn,
    ]
  );

  return {
    download: {
      settings: downloadSettings,
      defaults: downloadDefaults,
      status: downloadStatus,
      loading: downloadLoading,
      onChange: handleDownloadChange,
      onSubmit: handleDownloadSubmit,
    },
    apiKeys: {
      form: apiKeysForm,
      meta: apiKeysMeta,
      clearState: apiKeysClearState,
      status: apiKeysStatus,
      onChange: handleApiKeyChange,
      onClear: handleApiKeyClear,
      onSubmit: handleApiKeysSubmit,
    },
    spotdlStatus,
  };
};
