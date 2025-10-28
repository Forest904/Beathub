import { get, put } from './http';
import { endpoints } from './client';

export const fetchDownloadSettings = () => get(endpoints.settings.download());

export const updateDownloadSettings = (payload) => put(endpoints.settings.download(), payload);

export const fetchSettingsStatus = () => get(endpoints.settings.status());
