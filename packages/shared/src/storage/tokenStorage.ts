import type { TokenStorageOptions, TokenStorage } from "./types.js";
import { createMemoryStorage } from "./memoryStorage.js";

export const createTokenStorage = (
  options: TokenStorageOptions = {},
): TokenStorage => {
  const key = options.key ?? "auth_token";
  const storage = options.storage ?? createMemoryStorage();

  return {
    read: () => storage.getItem(key),
    write: (value: string) => storage.setItem(key, value),
    clear: () => storage.removeItem(key),
  };
};
