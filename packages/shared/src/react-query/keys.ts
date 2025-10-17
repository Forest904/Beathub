export const queryKeys = {
  downloads: {
    root: ["downloads"] as const,
    history: () => ["downloads", "history"] as const,
    job: (id: string | number) => ["downloads", "job", id] as const,
    progress: () => ["downloads", "progress"] as const,
  },
  artists: {
    search: (params: Record<string, unknown>) => ["artists", params] as const,
    popular: (params: Record<string, unknown>) => ["artists", "popular", params] as const,
  },
  playlists: {
    root: ["playlists"] as const,
    list: (params: Record<string, unknown>) => ["playlists", "list", params] as const,
    detail: (id: string | number) => ["playlists", "detail", id] as const,
  },
  config: {
    frontend: () => ["config", "frontend"] as const,
  },
} as const;
