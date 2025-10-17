import React, { useCallback, useEffect } from "react";
import { FlatList, Pressable, RefreshControl, Text, View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";

import { usePlaylistSummariesQuery } from "@cd-collector/shared/react-query";
import type { PlaylistSummary } from "@cd-collector/shared/api";
import Skeleton from "../components/Skeleton";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { useSnackbar } from "../providers/SnackbarProvider";
import type { RootStackParamList } from "../navigation/types";

type Navigation = NativeStackNavigationProp<RootStackParamList>;

const PlaylistsScreen: React.FC = () => {
  const navigation = useNavigation<Navigation>();
  const snackbar = useSnackbar();
  const insets = useSafeAreaInsets();
  const query = usePlaylistSummariesQuery({ per_page: 20 });

  useEffect(() => {
    if (query.error) {
      snackbar.showError("Could not load playlists.");
    }
  }, [query.error, snackbar]);

  const onRefresh = useCallback(async () => {
    try {
      await query.refetch();
    } catch {
      /* handled via snackbar */
    }
  }, [query]);

  const renderItem = useCallback(
    ({ item }: { item: PlaylistSummary }) => (
      <Pressable
        onPress={() =>
          navigation.navigate("PlaylistDetail", {
            playlistId: item.id,
            title: item.name,
          })
        }
        className="mb-4 rounded-3xl bg-slate-900/85 p-4"
      >
        <Text className="text-lg font-semibold text-slate-100">{item.name}</Text>
        {item.description ? (
          <Text numberOfLines={2} className="mt-1 text-sm text-slate-400">
            {item.description}
          </Text>
        ) : null}
        <View className="mt-3 flex-row items-center justify-between">
          <Text className="text-xs uppercase tracking-wide text-slate-500">
            {item.track_count} tracks
          </Text>
          {item.updated_at ? (
            <Text className="text-xs text-slate-500">
              Updated {new Date(item.updated_at).toLocaleDateString()}
            </Text>
          ) : null}
        </View>
      </Pressable>
    ),
    [navigation],
  );

  return (
    <View className="flex-1 bg-slate-950">
      <FlatList
        data={query.data?.items ?? []}
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
        ListEmptyComponent={
          query.isLoading ? (
            <View>
              {Array.from({ length: 5 }).map((_, index) => (
                <Skeleton key={index.toString()} height={92} style={{ marginBottom: 16 }} />
              ))}
            </View>
          ) : query.error ? (
            <ErrorState
              message={(query.error as Error).message}
              action={
                <Pressable
                  className="rounded-full bg-sky-500 px-4 py-2"
                  onPress={() => query.refetch()}
                >
                  <Text className="text-sm font-semibold text-white">Retry</Text>
                </Pressable>
              }
            />
          ) : (
            <EmptyState
              title="No playlists yet"
              description="Create playlists from your downloads on the web and they will appear here."
            />
          )
        }
      />
    </View>
  );
};

export default PlaylistsScreen;
