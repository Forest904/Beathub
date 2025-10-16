import { endpoints, httpGet } from "../api/index.js";
import { createPollingSubscription, PollingSubscriptionConfig, Subscription } from "./pollingSubscription.js";

export interface ProgressSubscriptionOptions<T> extends Partial<Omit<PollingSubscriptionConfig<T | null>, "poll">> {
  snapshotUrl?: string;
}

export const createProgressSubscription = <T = Record<string, unknown>>(
  options: ProgressSubscriptionOptions<T> = {},
): Subscription => {
  const snapshotUrl = options.snapshotUrl ?? endpoints.progress.snapshot();
  return createPollingSubscription<T | null>({
    intervalMs: 3000,
    maxIntervalMs: 10000,
    backoffMultiplier: 2,
    jitterRatio: 0.2,
    ...options,
    poll: async () => {
      try {
        const data = await httpGet<T>(snapshotUrl, {
          validateStatus: (status: number) => status === 204 || (status >= 200 && status < 300),
        });
        return data ?? null;
      } catch (error) {
        throw error;
      }
    },
  });
};
