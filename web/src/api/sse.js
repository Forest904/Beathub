import { createProgressSubscription as createSharedProgressSubscription, createPollingSubscription, PollingSubscription } from '@cd-collector/shared/eventing';
import { endpoints } from './client';

export const createProgressSubscription = (url, handlers = {}) => {
  const snapshotUrl = url
    ? url.replace('/progress/stream', '/progress/snapshot')
    : endpoints.progress.snapshot();

  return createSharedProgressSubscription({
    snapshotUrl,
    onData: handlers.onMessage,
    onError: handlers.onError,
    intervalMs: handlers.intervalMs || 3000,
  });
};

export { createPollingSubscription, PollingSubscription };
