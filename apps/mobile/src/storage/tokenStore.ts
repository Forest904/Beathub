import { createTokenStorage } from '@cd-collector/shared/storage';
import { secureStoreAdapter, asyncStorageAdapter } from './adapters';

export const secureTokenStorage = createTokenStorage({
  key: 'cdcollector-auth-token',
  storage: secureStoreAdapter,
});

export const localAsyncStorage = createTokenStorage({
  key: 'cdcollector-cache',
  storage: asyncStorageAdapter,
});
