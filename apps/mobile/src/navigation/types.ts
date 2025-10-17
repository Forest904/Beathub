import type { DownloadItem } from "@cd-collector/shared/api";

export type TabsParamList = {
  Discover: undefined;
  Releases: undefined;
  Playlists: undefined;
  DownloadQueue: undefined;
};

export type RootStackParamList = {
  MainTabs: undefined;
  PlaylistDetail: { playlistId: number; title?: string };
  ReleaseDetail: { item: DownloadItem };
};
