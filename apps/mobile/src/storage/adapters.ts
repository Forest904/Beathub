import * as SecureStore from 'expo-secure-store';
import AsyncStorage from '@react-native-async-storage/async-storage';
import type { StorageAdapter } from '@cd-collector/shared/storage';

export const secureStoreAdapter: StorageAdapter = {
  getItem: (key) => SecureStore.getItemAsync(key),
  setItem: (key, value) => SecureStore.setItemAsync(key, value, {
    keychainAccessible: SecureStore.WHEN_UNLOCKED,
  }),
  removeItem: (key) => SecureStore.deleteItemAsync(key),
};

export const asyncStorageAdapter: StorageAdapter = {
  getItem: (key) => AsyncStorage.getItem(key),
  setItem: (key, value) => AsyncStorage.setItem(key, value),
  removeItem: (key) => AsyncStorage.removeItem(key),
};
