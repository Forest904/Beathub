import type { StorageAdapter } from "./types.js";
import { createMemoryStorage } from "./memoryStorage.js";

declare global {
  interface Window {
    localStorage?: Storage;
  }
}

export const createBrowserStorage = (): StorageAdapter => {
  if (typeof window !== "undefined" && window.localStorage) {
    return {
      getItem: async (key: string) => window.localStorage.getItem(key),
      setItem: async (key: string, value: string) => {
        window.localStorage.setItem(key, value);
      },
      removeItem: async (key: string) => {
        window.localStorage.removeItem(key);
      },
    } satisfies StorageAdapter;
  }
  return createMemoryStorage();
};
