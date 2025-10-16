export interface StorageAdapter {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
  removeItem(key: string): Promise<void>;
}

export interface TokenStorageOptions {
  key?: string;
  storage?: StorageAdapter;
}

export interface TokenStorage {
  read(): Promise<string | null>;
  write(value: string): Promise<void>;
  clear(): Promise<void>;
}
