export class SSESubscription {
  constructor(url, { onMessage, onError, withCredentials = true } = {}) {
    this.url = url;
    this.onMessage = onMessage;
    this.onError = onError;
    this.withCredentials = withCredentials;
    this._source = null;
  }

  start() {
    const source = new EventSource(this.url, { withCredentials: this.withCredentials });
    this._source = source;
    if (typeof this.onMessage === 'function') {
      source.addEventListener('message', (event) => {
        try {
          const payload = JSON.parse(event.data);
          this.onMessage(payload, event);
        } catch (error) {
          if (this.onError) {
            this.onError(error);
          }
        }
      });
    }
    if (typeof this.onError === 'function') {
      source.addEventListener('error', this.onError);
    }
    return this;
  }

  stop() {
    if (this._source) {
      this._source.close();
      this._source = null;
    }
  }
}

export const createProgressSubscription = (url, handlers) => new SSESubscription(url, handlers);
