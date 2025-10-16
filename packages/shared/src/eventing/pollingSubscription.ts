export interface PollingSubscriptionHandlers<T> {
  onData?: (data: T) => void;
  onError?: (error: unknown) => void;
}

export interface PollingSubscriptionConfig<T> extends PollingSubscriptionHandlers<T> {
  poll: () => Promise<T>;
  intervalMs?: number;
  maxIntervalMs?: number;
  backoffMultiplier?: number;
  jitterRatio?: number;
}

export interface Subscription {
  start(): void;
  stop(): void;
  isRunning(): boolean;
}

export class PollingSubscription<T> implements Subscription {
  private timer: ReturnType<typeof setTimeout> | null = null;

  private readonly poll: () => Promise<T>;

  private readonly handlers: PollingSubscriptionHandlers<T>;

  private readonly baseInterval: number;

  private readonly maxInterval: number;

  private readonly backoffMultiplier: number;

  private readonly jitterRatio: number;

  private currentInterval: number;

  private inFlight = false;

  private active = false;

  constructor(config: PollingSubscriptionConfig<T>) {
    this.poll = config.poll;
    this.handlers = { onData: config.onData, onError: config.onError };
    this.baseInterval = config.intervalMs ?? 3000;
    this.maxInterval = config.maxIntervalMs ?? 15000;
    this.backoffMultiplier = config.backoffMultiplier ?? 1.5;
    this.jitterRatio = config.jitterRatio ?? 0.25;
    this.currentInterval = this.baseInterval;
  }

  start() {
    if (this.active) {
      return;
    }
    this.active = true;
    if (!this.inFlight && !this.timer) {
      void this.executePoll(true);
    }
  }

  stop() {
    this.active = false;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    this.currentInterval = this.baseInterval;
  }

  isRunning() {
    return this.active;
  }

  private scheduleNext() {
    if (!this.active) {
      return;
    }
    const jitter = this.currentInterval * this.jitterRatio * (Math.random() - 0.5) * 2;
    const nextInterval = Math.max(500, this.currentInterval + jitter);
    this.timer = setTimeout(() => {
      this.timer = null;
      void this.executePoll();
    }, nextInterval);
  }

  private async executePoll(resetInterval = false) {
    if (!this.active) {
      return;
    }
    this.inFlight = true;
    try {
      const data = await this.poll();
      this.handlers.onData?.(data);
      if (resetInterval) {
        this.currentInterval = this.baseInterval;
      } else {
        this.currentInterval = this.baseInterval;
      }
    } catch (error) {
      this.handlers.onError?.(error);
      this.currentInterval = Math.min(
        this.maxInterval,
        Math.round(this.currentInterval * this.backoffMultiplier),
      );
    } finally {
      this.inFlight = false;
      if (this.timer) {
        clearTimeout(this.timer);
        this.timer = null;
      }
      this.scheduleNext();
    }
  }
}

export const createPollingSubscription = <T>(config: PollingSubscriptionConfig<T>): Subscription =>
  new PollingSubscription<T>(config);
