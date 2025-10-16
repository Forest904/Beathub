export const queryKeys = {
  downloads: {
    root: ["downloads"] as const,
    history: () => ["downloads", "history"] as const,
    job: (id: string | number) => ["downloads", "job", id] as const,
  },
  artists: {
    search: (params: Record<string, unknown>) => ["artists", params] as const,
  },
  config: {
    frontend: () => ["config", "frontend"] as const,
  },
} as const;
