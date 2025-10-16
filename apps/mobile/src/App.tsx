import './lib/http';
import React from 'react';
import { SafeAreaView, Text } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { QueryClientProvider } from '@tanstack/react-query';
import { createQueryClient } from '@cd-collector/shared/react-query';

const queryClient = createQueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <SafeAreaView className="flex-1 items-center justify-center bg-slate-900">
      <StatusBar style="light" />
      <Text className="text-white text-2xl font-semibold">CD Collector</Text>
      <Text className="text-slate-300 mt-2 text-center px-8">
        Mobile workspace scaffold ready. Shared hooks and API clients are available via @cd-collector/shared.
      </Text>
    </SafeAreaView>
  </QueryClientProvider>
);

export default App;
