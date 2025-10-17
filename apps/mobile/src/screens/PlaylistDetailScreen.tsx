import React, { useCallback, useEffect } from "react";
import { FlatList, RefreshControl, Text, View } from "react-native";
import { RouteProp, useRoute } from "@react-navigation/native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { usePlaylistDetailQuery } from "@cd-collector/shared/react-query";
import type { PlaylistTrack } from "@cd-collector/shared/api";
import Skeleton from "../components/Skeleton";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { useSnackbar } from "../providers/SnackbarProvider";
import type { RootStackParamList } from "../navigation/types";

type PlaylistDetailRoute = RouteProp<RootStackParamList, "PlaylistDetail">;

const extractTrackTitle = (track: Record<string, unknown> | null) =>
  (track?.title as string) ||
  (track?.name as string) ||
  (track?.track_name as string) ||
  "Untitled";

const extractTrackArtist = (track: Record<string, unknown> | null) => {
  const artists = track?.artists;
  if (Array.isArray(artists)) {
    return artists.map(String).join(", ");
  }
  return (
    (track?.artist as string) ||
    (track?.artist_name as string) ||
    (track?.album_artist as string) ||
    "Unknown artist"
  );
};

const PlaylistDetailScreen: React.FC = () => {
  const { params } = useRoute<PlaylistDetailRoute>();
  const snackbar = useSnackbar();
  const insets = useSafeAreaInsets();
  const query = usePlaylistDetailQuery(params?.playlistId);

  useEffect(() => {
    if (query.error) {
      snackbar.showError("Unable to load playlist.");
    }
  }, [query.error, snackbar]);

  const onRefresh = useCallback(async () => {
    try {
      await query.refetch();
    } catch {
      /* handled elsewhere */
    }
  }, [query]);

  const renderItem = useCallback(
    ({ item, index }: { item: PlaylistTrack; index: number }) => {
      const snapshot = item.track ?? {};
      const title = extractTrackTitle(snapshot);
      const artist = extractTrackArtist(snapshot);
      const durationMs = snapshot?.duration_ms as number | undefined;
      const duration =
        typeof durationMs === "number"
          ? new Date(durationMs).toISOString().slice(14, 19)
          : null;

      return (
        <View className="mb-4 flex-row items-center rounded-3xl bg-slate-900/85 p-4">
          <View className="mr-4 h-10 w-10 items-center justify-center rounded-full bg-slate-800">
            <Text className="text-sm font-semibold text-slate-200">{index + 1}</Text>
          </View>
          <View className="flex-1">
            <Text numberOfLines={1} className="text-base font-semibold text-slate-100">
              {title}
            </Text>
            <Text numberOfLines={1} className="text-sm text-slate-400">
              {artist}
            </Text>
          </View>
          {duration ? <Text className="text-xs text-slate-500">{duration}</Text> : null}
        </View>
      );
    },
    [],
  );

  return (
    <View className="flex-1 bg-slate-950">
      <FlatList
        data={query.data?.tracks ?? []}
        keyExtractor={(item) => item.id.toString()}
        renderItem={renderItem}
        contentContainerStyle={{
          paddingHorizontal: 24,
          paddingTop: insets.top + 16,
          paddingBottom: insets.bottom + 32,
        }}
        refreshControl={
          <RefreshControl
            refreshing={query.isFetching}
            onRefresh={onRefresh}
            tintColor="#38bdf8"
          />
        }
        ListHeaderComponent={
          query.data ? (
            <View className="mb-6">
              <Text className="text-2xl font-semibold text-slate-100">
                {query.data.name}
              </Text>
              {query.data.description ? (
                <Text className="mt-2 text-sm text-slate-300">{query.data.description}</Text>
              ) : null}
              <Text className="mt-2 text-xs uppercase tracking-wide text-slate-500">
                {query.data.track_count} tracks total
              </Text>
            </View>
          ) : null
        }
        ListEmptyComponent={
          query.isLoading ? (
            <View>
              <Skeleton height={62} style={{ marginBottom: 16 }} />
              <Skeleton height={62} style={{ marginBottom: 16 }} />
              <Skeleton height={62} />
            </View>
          ) : query.error ? (
            <ErrorState
              message={(query.error as Error).message}
              action={
                <Text className="text-sm text-slate-300">
                  Pull to retry once the network stabilizes.
                </Text>
              }
            />
          ) : (
            <EmptyState
              title="Playlist is empty"
              description="Add tracks from your downloads using the web app to populate this playlist."
            />
          )
        }
      />
    </View>
  );
};

export default PlaylistDetailScreen;
