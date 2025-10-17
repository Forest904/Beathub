import "./lib/http";
import React from "react";
import { StatusBar } from "expo-status-bar";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { QueryClientProvider } from "@tanstack/react-query";
import { createQueryClient } from "@cd-collector/shared/react-query";

import Navigation from "./navigation";
import { SnackbarProvider } from "./providers/SnackbarProvider";

const queryClient = createQueryClient();

const App = () => (
  <GestureHandlerRootView style={{ flex: 1 }}>
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <SnackbarProvider>
          <Navigation />
          <StatusBar style="light" />
        </SnackbarProvider>
      </QueryClientProvider>
    </SafeAreaProvider>
  </GestureHandlerRootView>
);

export default App;
