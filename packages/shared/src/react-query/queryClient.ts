import { QueryClient, QueryClientConfig } from "@tanstack/react-query";

export const createQueryClient = (config?: QueryClientConfig) =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: 1,
        refetchOnWindowFocus: false,
        refetchOnReconnect: true,
      },
      mutations: {
        retry: 0,
      },
    },
    ...config,
  });
