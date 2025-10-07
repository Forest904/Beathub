export const isNonEmptyString = (value) => typeof value === 'string' && value.trim().length > 0;
export const isFunction = (value) => typeof value === 'function';
export const isBrowser = () => typeof window !== 'undefined' && typeof document !== 'undefined';
